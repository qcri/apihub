import logging
from enum import Enum

import redis
from pydantic import Field, BaseModel
from prometheus_client import Counter, Histogram
from dotenv import load_dotenv

load_dotenv()

from pipeline import ProcessorSettings, Processor, Settings, DescribeMessage
from apihub import __worker__, __version__


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedisSettings(Settings):
    redis: str = Field("redis://localhost:6379/1", title="redis url")


class Status(str, Enum):
    ACCEPTED = "ACCEPTED"
    PROCESSED = "PROCESSED"


class Result(BaseModel):
    user: str
    api: str
    status: Status
    result: dict = dict()


class ResultWriter(Processor):
    """ResultWriter collects results from API service worker, and
    store these results in Redis
    """

    api_counter = Counter(
        "api_requests_total",
        "API requests",
        ["api", "user", "status"],
    )
    request_duration = Histogram(
        "api_process_time_seconds",
        "Processing time (seconds)",
        labelnames=["api"],
    )

    def __init__(self) -> None:
        settings = ProcessorSettings(
            name=__worker__ + " ResultWriter",
            version=__version__,
            description="write results to redis",
            debug=True,
            monitoring=True,
        )

        super().__init__(settings, input_class=dict, output_class=None)

    def setup(self) -> None:
        settings = RedisSettings()
        self.redis = redis.Redis.from_url(settings.redis)

    def process_special_message(self, message: DescribeMessage) -> None:
        print(message.input_schema)
        print(message.output_schema)

    def process(self, message_content, message_id):
        result = Result.parse_obj(message_content)
        if result.status == Status.PROCESSED:
            result.result = {
                k: message_content.get(k) for k in self.message.logs[-1].updated
            }

        self.api_counter.labels(api=result.api, user=result.user, status=result.status)

        if self.redis.get(message_id) is not None:
            logger.warning("Found result with key %s, overwriting...", message_id)

        self.redis.set(message_id, result.json(), ex=86400)
        return None


def main():
    writer = ResultWriter()
    writer.parse_args()
    writer.start()


if __name__ == "__main__":
    main()
