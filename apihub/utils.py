import uuid
import datetime

from pydantic import Field
import redis

from pipeline import Settings, Pipeline


def make_key():
    return str(uuid.uuid1())


def initial_state(key):
    state = {
        "key": key,
        "status": "accepted",
        "submissionTime": datetime.datetime.utcnow().isoformat(),
    }
    return state


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
