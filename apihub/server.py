import sys
import functools
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request, Query, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from dotenv import load_dotenv
from pipeline import Message, Settings, Command, CommandActions, Monitor
from apihub_users.security.depends import RateLimiter, RateLimits, require_user
from apihub_users.security.router import router as security_router
from apihub_users.subscription.depends import require_subscription
from apihub_users.subscription.router import router as application_router

from apihub.utils import State, make_topic, make_key, Result, Status
from apihub import __worker__, __version__


load_dotenv(override=False)

monitor = Monitor()
operation_counter = monitor.use_counter(
    "APIHub",
    "API operation counts",
    labels=["api", "user", "operation"],
)


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
    result: Dict[str, Any] = Field(title="result")


@api.get("/", include_in_schema=False, dependencies=[Depends(ip_rate_limited)])
async def root():
    return {
        __worker__: __version__,
    }


@api.get(
    "/define/{application}",
    dependencies=[Depends(ip_rate_limited)],
)
async def define_service(
    application: str,
    # username: str = Depends(require_admin),
):
    """ """

    get_state().write(make_topic(application), Command(action=CommandActions.Define))


@api.post(
    "/async/{application}",
    response_model=AsyncAPIRequestResponse,
    dependencies=[Depends(ip_rate_limited)],
)
async def async_service(
    application: str, request: Request, username: str = Depends(require_subscription)
):
    """generic handler for async api."""

    operation_counter.labels(api=application, user=username, operation="received").inc()

    key = make_key()

    dct: Dict[str, Any] = {}

    # inject form data
    dct.update(await request.form())

    # inject query parameters
    dct.update(request.query_params)

    # inject user information
    info = Result(
        user=username,
        api=application,
        status=Status.ACCEPTED,
    )

    accept_notification = Message(content=info.dict(), id=key)
    get_state().write(make_topic("result"), accept_notification)

    # send job request to its approporate topic
    info.status = Status.PROCESSED
    dct.update(info.dict())
    get_state().write(make_topic(application), Message(content=dct, id=key))

    operation_counter.labels(api=application, user=username, operation="accepted").inc()

    return AsyncAPIRequestResponse(success=True, key=key)


@api.get("/async/{application}", dependencies=[Depends(ip_rate_limited)])
async def async_service_result(
    application: str,
    key: str = Query(
        ...,
        title="unique key returned by a request",
        example="91cb3a68-dd59-11ea-9f2a-82527949ac01",
    ),
    username=Depends(require_user),
):
    """ """

    result = get_redis().get(key)
    if result is None:
        operation_counter.labels(
            api=application, user=username, operation="result_not_found"
        ).inc()
        raise HTTPException(
            status_code=404,
            detail="Result with this key cannot be found",
        )

    result = Result.parse_raw(result)

    if result.status == Status.ACCEPTED:
        raise HTTPException(
            status_code=202,
            detail="Result is not ready",
        )
    elif result.status != Status.PROCESSED:
        operation_counter.labels(
            api=application, user=username, operation="error"
        ).inc()
        # FIXME change status code
        raise HTTPException(
            status_code=501,
            detail="Unexpected error happened",
        )

    operation_counter.labels(
        api=application, user=username, operation="result_served"
    ).inc()

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


class ServerSettings(Settings):
    port: int = 5000
    log_level: str = "debug"
    reload: bool = True


def main():
    import uvicorn

    monitor.expose()

    settings = ServerSettings()
    settings.parse_args(args=sys.argv)
    uvicorn.run(
        "apihub.server:api",
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level,
        reload=settings.reload,
    )


if __name__ == "__main__":
    main()
