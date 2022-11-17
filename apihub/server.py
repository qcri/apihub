import sys
import functools
import logging
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request, Query, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from fastapi_jwt_auth import AuthJWT
from fastapi.openapi.utils import get_openapi
from dotenv import load_dotenv
from pipeline import Message, Settings, Command, CommandActions, Monitor

from .common.db_session import db_context
from .activity.schemas import ActivityStatus, ActivityCreate
from .activity.queries import ActivityQuery
from .security.depends import RateLimiter, RateLimits, require_user
from .security.router import router as security_router
from .subscription.depends import require_subscription
from .subscription.router import router as application_router
from .subscription.schemas import SubscriptionBase
from .utils import (
    State,
    make_topic,
    make_key,
    Result,
    DefinitionManager,
)
from . import __worker__, __version__

load_dotenv(override=False)

monitor = Monitor()
operation_counter = monitor.use_counter(
    "APIHub",
    "API operation counts",
    labels=["api", "user", "operation"],
)


@functools.lru_cache(maxsize=None)
def get_state():
    logging.basicConfig(level=logging.DEBUG)
    return State(logger=logging)


def get_redis():
    return get_state().redis


@functools.lru_cache(maxsize=None)
def get_definition_manager():
    return DefinitionManager(redis=get_redis())


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
    tags=["security"],
    dependencies=[Depends(ip_rate_limited)],
)
api.include_router(
    application_router, tags=["subscription"], dependencies=[Depends(ip_rate_limited)]
)


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
    include_in_schema=False,
    dependencies=[Depends(ip_rate_limited)],
)
async def define_service(
    application: str,
    # username: str = Depends(require_admin),
):
    """ """

    get_state().write(make_topic(application), Command(action=CommandActions.Define))

    return {"define": f"application {application}"}


@api.post(
    "/async/{application}",
    include_in_schema=False,
    response_model=AsyncAPIRequestResponse,
    dependencies=[Depends(ip_rate_limited)],
)
async def async_service(
    request: Request,
    background_tasks: BackgroundTasks,
    subscription: SubscriptionBase = Depends(require_subscription),
):
    """generic handler for async api."""

    username = subscription.username
    tier = subscription.tier
    application = subscription.application
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
        status=ActivityStatus.ACCEPTED,
    )

    accept_notification = Message(content=info.dict(), id=key)
    get_state().write(make_topic("result"), accept_notification)

    # send job request to its appropriate topic
    info.status = ActivityStatus.PROCESSED
    dct.update(info.dict())
    get_state().write(make_topic(application), Message(content=dct, id=key))

    operation_counter.labels(api=application, user=username, operation="accepted").inc()

    activity = ActivityCreate(
        request=f"/async/{application}",
        username=username,
        tier=tier,
        status=ActivityStatus.ACCEPTED,
        request_key=str(key),
        result=str(info.dict()),
        payload=str(dct),
        ip_address=str(request.client.host),
        latency=0.0,
    )

    def add_activity_task(activity):
        with db_context() as session:
            ActivityQuery(session).create_activity(activity)

    background_tasks.add_task(add_activity_task, activity=activity)
    return AsyncAPIRequestResponse(success=True, key=key)


@api.get(
    "/async/{application}",
    dependencies=[Depends(ip_rate_limited)],
    include_in_schema=False,
)
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

    if result.status == ActivityStatus.ACCEPTED:
        raise HTTPException(
            status_code=202,
            detail="Result is not ready",
        )
    elif result.status != ActivityStatus.PROCESSED:
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


@api.post(
    "/sync/{application}",
    include_in_schema=False,
)
def extract_components(schema, components):
    definitions = schema.get("definitions")
    if definitions:
        del schema["definitions"]
        components.update(definitions)


def get_paths(redis=get_redis()):
    paths = {}
    components_schemas = {}
    security_schemes = {}
    definitions = DefinitionManager(redis=redis)

    for name, definition in definitions.get_all():
        security_schemes[f"api_{name}"] = {
            "type": "http",
            "description": f"need token obtained from /token/{name}",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }

        security = [{f"api_{name}": []}]

        # asynchronized API
        path = {}

        operation = {
            "tags": ["app"],
            "summary": definition.description,
            "description": definition.description,
            "security": security,
        }

        extract_components(definition.input_schema, components_schemas)

        operation["requestBody"] = {
            "content": {
                "application/json": {
                    "schema": definition.input_schema,  # ["properties"],
                }
            },
            "required": True,
        }

        path["post"] = operation

        operation = {
            "tags": ["app"],
            "summary": "obtain results from previous post requests",
            "description": definition.description,
            "security": security,
        }

        parameters = [
            {
                "name": "key",
                "in": "query",
                "description": "the unique key obtained from post request",
                "required": True,
                "type": "string",
                "format": "string",
            }
        ]
        # a strange way to sort parameters maybe
        operation["parameters"] = list(
            {param["name"]: param for param in parameters}.values()
        )

        extract_components(definition.output_schema, components_schemas)

        operation["responses"] = {
            "200": {
                "description": "success",
                "content": {
                    "application/json": {
                        "schema": definition.output_schema,
                    }
                },
            }
        }

        path["get"] = operation

        paths[f"/async/{name}"] = path

        # synchronized API
        path = {}
        operation = {
            "tags": ["app"],
            "summary": definition.description,
            "description": definition.description,
            "security": security,
            "requestBody": {
                "content": {
                    "application/json": {
                        "schema": definition.input_schema,  # ["properties"],
                    }
                },
                "required": True,
            },
            "responses": {
                "200": {
                    "description": "success",
                    "content": {
                        "application/json": {
                            "schema": definition.output_schema,
                        }
                    },
                }
            },
        }

        path["post"] = operation

        paths[f"/sync/{name}"] = path

    return paths, components_schemas, security_schemes


def custom_openapi(app=api):
    # if app.openapi_schema:
    #    return app.openapi_schema

    openapi_schema = get_openapi(
        title="APIHub",
        version="0.1.0",
        description="API for AI",
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "https://raw.githubusercontent.com/yifan/apihub/master/images/APIHub-logo.png"
    }
    paths, components_schemas, security_schemes = get_paths()
    openapi_schema["paths"].update(paths)
    openapi_schema["components"]["schemas"].update(components_schemas)
    openapi_schema["components"]["securitySchemes"] = security_schemes

    app.openapi_schema = openapi_schema
    return app.openapi_schema


api.openapi = custom_openapi


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
