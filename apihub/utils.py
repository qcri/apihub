import uuid
from datetime import datetime
from typing import Dict, Any
from enum import Enum

from pydantic import Field, BaseModel
import redis

from pipeline import Settings, Pipeline


DEFINITION = "api:definition"


class Status(str, Enum):
    ACCEPTED = "ACCEPTED"
    PROCESSED = "PROCESSED"


class Result(BaseModel):
    user: str
    api: str
    status: Status
    submission_time: str = datetime.utcnow().isoformat()
    result: Dict[str, Any] = dict()


class RedisSettings(Settings):
    redis: str = Field("redis://localhost:6379/1", title="redis url")


class State:
    def __init__(self):
        self.pipeline = Pipeline()
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
    return f"api-{service_name}"
