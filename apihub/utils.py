import uuid
from datetime import datetime
from typing import Dict, Any

import os

from prometheus_client import (
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY,
    multiprocess,
    CollectorRegistry,
)
from starlette import status
from starlette.requests import Request
from starlette.responses import Response

from pydantic import Field, BaseModel
import redis

from pipeline import Settings, Pipeline, Definition

from .activity.schemas import ActivityStatus


DEFINITION = "api:definition"


def utcnow_isoformat():
    return datetime.utcnow().isoformat()


class Result(BaseModel):
    user: str
    api: str
    status: ActivityStatus
    submission_time: str = Field(default_factory=utcnow_isoformat)
    result: Dict[str, Any] = dict()


class RedisSettings(Settings):
    redis: str = Field("redis://localhost:6379/1", title="redis url")


class State:
    def __init__(self, logger):
        self.pipeline = Pipeline(logger=logger)
        settings = RedisSettings()
        settings.parse_args(args=[])
        self.redis = redis.Redis.from_url(settings.redis)

    def write(self, name, message):
        # add topic to pipeline if it is not already done
        if name not in self.pipeline.destinations:
            self.pipeline.add_destination_topic(name)
        # write message to pipeline
        self.pipeline.destination_of(name).write(message)


def make_key():
    return str(uuid.uuid1())


def make_topic(service_name: str):
    return service_name


from fastapi import APIRouter

metrics_router = APIRouter()


@metrics_router.get("/metrics", include_in_schema=False)
def metrics_route(request: Request):
    """
    Endpoint for Prometheus metrics_route. Code taken from prometheus_client examples.
    Examples:
        app.add_middleware(PrometheusMiddleware, {params})
        app.add_route("/metrics_route", metrics_route)
    """
    registry = REGISTRY
    if "prometheus_multiproc_dir" in os.environ:
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)

    data = generate_latest(registry)
    response_headers = {
        "Content-type": CONTENT_TYPE_LATEST,
        "Content-Length": str(len(data)),
    }
    return Response(data, status_code=status.HTTP_200_OK, headers=response_headers)


class DefinitionManager(object):
    """manages definition obtained from workers"""

    def __init__(self, redis):
        self.redis = redis

    def add(self, definition):
        self.redis.hset(DEFINITION, definition.source.topic, definition.json())

    def delete(self, topic):
        self.redis.hdel(DEFINITION, topic)

    def delete_all(self):
        for topic in self.redis.hkeys(DEFINITION):
            self.delete(topic)

    def get(self, topic):
        definition_json = self.redis.hget(DEFINITION, topic)
        definition = Definition.parse_raw(definition_json)
        return definition

    def get_all(self):
        for topic, definition_json in self.redis.hgetall(DEFINITION).items():
            topic = topic.decode("utf-8")
            definition = Definition.parse_raw(definition_json)
            yield topic, definition
