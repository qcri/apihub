import pdb

import pytest
from fastapi import FastAPI
from apihub.common.db_session import create_session


from fastapi.testclient import TestClient

from apihub.subscription.router import router as sub_router
from apihub.security.router import router as sec_router
from apihub.activity.queries import ActivityQuery
from apihub.activity.schemas import ActivityStatus
from .test_activity import ActivityFactory

message_id = "ab7fe542-bdf2-11eb-b401-f21898b454f0"


@pytest.fixture(scope="function")
def client(db_session):
    def _create_session():
        try:
            yield db_session
        finally:
            pass

    app = FastAPI()
    app.include_router(sub_router)
    app.include_router(sec_router)
    app.dependency_overrides[create_session] = _create_session
    ActivityFactory._meta.sqlalchemy_session = db_session
    ActivityFactory._meta.sqlalchemy_session_persistence = "commit"
    ActivityFactory(
        username="tester",
        request="async/app1",
        request_key=message_id,
        status=ActivityStatus.ACCEPTED,
    )
    pdb.set_trace()
    yield TestClient(app)


class TestResultWriter:
    def test_basic(self, client, db_session, monkeypatch):
        monkeypatch.setenv("IN_KIND", "FILE")
        monkeypatch.setenv("MONITORING", "FALSE")
        monkeypatch.setenv("IN_FILENAME", "tests/fixtures/result_input.txt")
        from apihub.result import ResultWriter

        try:
            writer = ResultWriter()
            writer.parse_args()
            assert writer.settings.monitoring is False
            writer.start()
        except Exception:
            pytest.fail("worker raised exception")

        activity = ActivityQuery(db_session).get_activity_by_key(message_id)
        assert activity.status == ActivityStatus.PROCESSED

    def test_command(self, monkeypatch):
        monkeypatch.setenv("IN_KIND", "FILE")
        monkeypatch.setenv("MONITORING", "FALSE")
        monkeypatch.setenv("IN_FILENAME", "tests/fixtures/result_input.txt")
        from apihub.result import ResultWriter

        try:
            writer = ResultWriter()
            writer.parse_args()
            writer.start()
        except Exception:
            pytest.fail("worker raised exception")
