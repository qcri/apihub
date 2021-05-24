import json
import logging

import redis
from pydantic import Field
from prometheus_client import Counter, Histogram
from dotenv import load_dotenv

load_dotenv()

from pipeline import ProcessorSettings, Processor, Settings, DescribeMessage
from apihub import __worker__, __version__


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedisSettings(Settings):
    redis: str = Field("redis://localhost:6379/1", title="redis url")


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
        # get results from service worker, it assumes that service worker
        # use a single update to store results from it
        self.logger.debug(message_content)
        info = message_content.get("info")
        if info:
            self.api_counter.labels(
                api=info.get("api"), user=info.get("email"), status=info.get("status")
            )
        else:
            pass
            # self.api_counter.labels(
            #     api=info.get("api"), user=info.get("email"), status="resultReady"
            # )

        if self.redis.get(message_id) is not None:
            logger.warn("Found result with key %s, overwriting...", message_id)

        self.redis.set(message_id, json.dumps(message_content), ex=86400)
        return None


def main():
    writer = ResultWriter()
    writer.parse_args()
    writer.start()


if __name__ == "__main__":
    main()
