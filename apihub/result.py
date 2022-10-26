import redis
from prometheus_client import Counter, Histogram
from dotenv import load_dotenv

from pipeline import ProcessorSettings, Processor, Command, CommandActions, Definition
from apihub.utils import Result, Status, RedisSettings, DEFINITION
from apihub import __worker__, __version__

from apihub_users.usage.models import Activity

load_dotenv()


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

    def process_command(self, command: Command) -> None:
        self.logger.info("Processing COMMAND")
        if command.action == CommandActions.Define:
            definition = Definition.parse_obj(command.content)
            self.logger.info(definition)
            self.redis.hset(DEFINITION, definition.source.topic, definition.json())
            self.logger.info(
                f"{definition.source.topic} definition:\n{definition.json()}"
            )

    def process(self, message_content, message_id):
        self.logger.info("Processing MESSAGE")
        result = Result.parse_obj(message_content)
        if result.status == Status.PROCESSED:
            result.result = {
                k: message_content.get(k) for k in self.message.logs[-1].updated
            }

        self.api_counter.labels(api=result.api, user=result.user, status=result.status)

        if self.redis.get(message_id) is not None:
            self.logger.warning("Found result with key %s, overwriting...", message_id)

        r = result.json()
        self.redis.set(message_id, r, ex=86400)
        Activity.update_activity(message_id, **{"status": "processed", "result": r})
        return None


def main():
    writer = ResultWriter()
    writer.parse_args()
    writer.start()


if __name__ == "__main__":
    main()
