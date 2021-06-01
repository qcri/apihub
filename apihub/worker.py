import logging

from pydantic import BaseModel
from dotenv import load_dotenv

from pipeline import ProcessorSettings, Processor
from apihub import __worker__, __version__


load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Input(BaseModel):
    id: str
    username: str
    api: str
    status: str


class Output(BaseModel):
    value: str


class ExampleWorker(Processor):
    """an example worker to used to test APIHub"""

    def __init__(self) -> None:
        settings = ProcessorSettings(
            name=__worker__ + " ExampleWorker",
            version=__version__,
            description="an example",
            debug=True,
            monitoring=True,
        )

        super().__init__(settings, input_class=Input, output_class=Output)

    def process(self, message_content, message_id):
        return Output(value=str(message_content))


def main():
    worker = ExampleWorker()
    worker.parse_args()
    worker.start()


if __name__ == "__main__":
    main()
