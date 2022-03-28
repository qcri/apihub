import sys
import functools
import logging
import logging.config
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request, Query, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from fastapi.openapi.utils import get_openapi
from jsonschema import validate
from dotenv import load_dotenv
from pipeline import Message, Settings, Command, CommandActions, Monitor
from apihub_users.security.depends import RateLimiter, RateLimits
from apihub_users.security.router import router as security_router
from apihub_users.subscription.depends import require_subscription
from apihub_users.subscription.router import router as application_router

from apihub.utils import (
    DefinitionManager,
    State,
    make_topic,
    make_key,
    Result,
    Status,
    metrics_router,
)
from apihub import __worker__, __version__


load_dotenv(override=False)


# logging.config.fileConfig('logging.conf', disable_existing_loggers=False)


monitor = Monitor()
operation_counter = monitor.use_counter(
    "APIHub",
    "API operation counts",
    labels=["api", "user", "operation"],
)


@functools.lru_cache(maxsize=None)
def get_state():
    logger = logging.getLogger("pipeline")
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
    logger.info("Setting up logger")
    return State(logger=logger)


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
    "/delete/definitions",
    include_in_schema=False,
    dependencies=[Depends(ip_rate_limited)],
)
async def delete_definitions():
    """ """
    get_definition_manager().delete_all()
    return {"success": True}


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
    application: str, request: Request, username: str = Depends(require_subscription)
):
    """generic handler for async api."""

    operation_counter.labels(api=application, user=username, operation="received").inc()

    key = make_key()

    dct: Dict[str, Any] = {}

    dct.update(await request.json())

    # inject query parameters
    dct.update(request.query_params)

    definition = get_definition_manager().get(application)
    validate(instance=dct, schema=definition.input_schema)

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
    username=Depends(require_subscription),
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
        key=key,
        result=result,
    )


@api.post(
    "/sync/{service_name}",
    include_in_schema=False,
)
async def sync_service(service_name: str):
    """generic synchronised api hendler"""
    # TODO synchronised service, basically it will wait and return results
    # when it is ready. It will have a timeout of 30 seconds


def extract_components(schema, components):
    definitions = schema.get("definitions")
    if definitions:
        del schema["definitions"]
        components.update(definitions)


def get_paths(redis=get_redis()):
    paths = {}
    components_schemas = {}
    definitions = DefinitionManager(redis=redis)
    for name, definition in definitions.get_all():
        path = {}

        # security = {
        #     "type": "http",
        #     "description": f"need token obtained from /token/{name}",
        #     "scheme": "bearer",
        #     "bearerFormat": "JWT",
        # }

        logging.basicConfig(level=logging.INFO)
        operation = {}
        operation["tags"] = ["app"]
        operation["summary"] = definition.description
        operation["description"] = definition.description
        # operation["security"] = security
        parameters = {}

        extract_components(definition.input_schema, components_schemas)

        operation["requestBody"] = {
            "content": {
                "application/json": {
                    "schema": definition.input_schema,  # ["properties"],
                }
            },
            "required": True,
        }
        operation["responses"] = {
            "200": {
                "description": "successful request",
                "status_code": 200,
                "content": {
                    "application/json": {"schema": AsyncAPIRequestResponse.schema()}
                },
            }
        }
        path["post"] = operation

        operation = {}
        operation["tags"] = ["app"]
        operation["summary"] = "obtain results from previous post requests"
        operation["description"] = definition.description
        # operation["security"] = security
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
    return paths, components_schemas


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
    paths, components_schemas = get_paths()
    openapi_schema["paths"].update(paths)
    openapi_schema["components"]["schemas"].update(components_schemas)
    app.openapi_schema = openapi_schema
    return app.openapi_schema


api.openapi = custom_openapi


class ServerSettings(Settings):
    port: int = 5000
    log_level: str = "debug"
    monitoring: bool = False
    reload: bool = False
    debug: bool = False


def main():
    import uvicorn

    settings = ServerSettings()
    settings.parse_args(args=sys.argv)

    if settings.monitoring:
        api.include_router(metrics_router)

    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(levelprefix)s %(message)s",
                "use_colors": None,
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO"},
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["default"],
                "propagate": True,
            },
            "uvicorn.access": {
                "handlers": ["access"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }

    log_config["loggers"]["pipeline"] = {"handlers": ["default"], "level": "INFO"}

    uvicorn.run(
        "apihub.server:api",
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level,
        log_config=log_config,
        # no_access_log=True,
        # use_colors=True,
        reload=settings.reload,
        debug=settings.debug,
    )


if __name__ == "__main__":
    main()
