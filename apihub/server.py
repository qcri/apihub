import json
import functools

from fastapi import FastAPI, HTTPException, Request, Query, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
import uvicorn
from pipeline import Message
from dotenv import load_dotenv

from apihub.security.depends import RateLimiter, RateLimits, require_user
from apihub.security.router import router as security_router
from apihub.subscription.helpers import record_usage
from apihub.subscription.depends import require_subscription
from apihub.subscription.router import router as application_router
from apihub.utils import make_key, initial_state, State
from apihub import __worker__, __version__


load_dotenv(override=False)


@functools.lru_cache(maxsize=None)
def get_state():
    return State()


def get_redis():
    return get_state().redis


ip_rate_limited = RateLimiter(
    key="ip", limits=RateLimits(limit=10, window_secs=10), redis=get_redis()
)


class JWTSettings(BaseModel):
    authjwt_secret_key: str = "secret"


# callback to get your configuration
@AuthJWT.load_config
def jwt_get_config():
    return JWTSettings()


api = FastAPI(
    title=__worker__,
    description="API for TANBIH ML models",
    version=__version__,
)
api.include_router(
    security_router,
    #     prefix='/security',
    #     tags=['security'],
    dependencies=[Depends(ip_rate_limited)],
)
api.include_router(application_router, dependencies=[Depends(ip_rate_limited)])


@api.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


class AsyncAPIRequestResponse(BaseModel):
    success: bool = Field(title="boolean", example=True)
    key: str = Field(title="unique key", example="91cb3a68-dd59-11ea-9f2a-82527949ac01")


class AsyncAPIResultResponse(BaseModel):
    success: bool = Field(title="boolean", example=True)
    key: str = Field(title="unique key", example="91cb3a68-dd59-11ea-9f2a-82527949ac01")
    result: dict = Field(title="result")


def make_topic(service_name: str):
    return f"api-{service_name}"


def get_result(key: str):
    result = get_redis().get(key)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Result with this key cannot be found",
        )

    result = json.loads(result)

    status = result.get("status")
    if status == "jobAccepted":
        raise HTTPException(
            status_code=202,
            detail="Result is not ready",
        )
    elif status == "resultReady":
        return result
    else:
        # FIXME change status code
        raise HTTPException(
            status_code=501,
            detail="Unexpected error happened",
        )


@api.get("/", include_in_schema=False, dependencies=[Depends(ip_rate_limited)])
async def root():
    return {
        __worker__: __version__,
    }


class ClientInfo(BaseModel):
    user: str
    api: str
    status: str


class Extra(BaseModel):
    info: ClientInfo


@api.post(
    "/async/{application}",
    response_model=AsyncAPIRequestResponse,
    dependencies=[Depends(ip_rate_limited)],
)
async def async_service(
    application: str, request: Request, username: str = Depends(require_subscription)
):
    """generic handler for async api."""
    # TODO change service_name to app_name or application

    record_usage(username, application, redis=get_redis())

    key = make_key()

    dct = {
        "id": key,
    }

    # inject form data
    dct.update(await request.form())

    # inject query parameters
    dct.update(request.query_params)

    # inject user information

    info = ClientInfo(
        user=username,
        api=application,
        status="jobAccepted",
    )

    # inital result "jobAccepted"
    initialResult = Message(content=initial_state(key), id=key)
    initialResult.update_content(Extra(info=info))

    dct.update(
        {
            "info": info.dict(),
        }
    )

    # write a temporary 'NotReady' result
    get_state().write(make_topic("result"), initialResult)
    # send job to its approporate topic
    get_state().write(make_topic(application), Message(content=dct, id=key))

    return AsyncAPIRequestResponse(success=True, key=key)


@api.get("/async/{service_name}", dependencies=[Depends(ip_rate_limited)])
async def async_service_result(
    service_name: str,
    key: str = Query(
        ...,
        title="unique key returned by a request",
        example="91cb3a68-dd59-11ea-9f2a-82527949ac01",
    ),
    user=Depends(require_user),
):
    """ """

    result = get_result(key)

    return AsyncAPIResultResponse(
        success=True,
        key=result.get("key"),
        result=result,
    )


@api.post("/sync/{service_name}")
async def sync_service(service_name: str):
    """generic synchronised api hendler"""
    # TODO synchronised service, basically it will wait and return results
    # when it is ready. It will have a timeout of 30 seconds


def main():
    uvicorn.run("server:api", host="0.0.0.0", port=8000, log_level="debug", reload=True)


if __name__ == "__main__":
    main()
