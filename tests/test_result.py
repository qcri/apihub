import pytest

# from apihub.activity.queries import ActivityQuery
# from apihub.activity.schemas import ActivityStatus
# from .test_activity import ActivityFactory


message_id = "ab7fe542-bdf2-11eb-b401-f21898b454f0"


# @pytest.fixture(scope="function")
# def query(db_session):
#     ActivityFactory._meta.sqlalchemy_session = db_session
#     ActivityFactory._meta.sqlalchemy_session_persistence = "commit"
#     ActivityFactory(
#         username="tester",
#         request="async/app1",
#         request_key=message_id,
#         status=ActivityStatus.ACCEPTED,
#     )
#     yield ActivityQuery(db_session)


class TestResultWriter:
    def test_basic(self, db_session, monkeypatch):
        # activity = query.get_activity_by_key(message_id)
        # assert activity.status == ActivityStatus.ACCEPTED

        monkeypatch.setenv("MONITORING", "FALSE")
        from apihub.result import ResultWriter

        try:
            writer = ResultWriter()
            writer.parse_args(
                "--in-kind FILE --in-filename tests/fixtures/result_input.txt --no-in-content-only".split()
            )
            writer.set_db_session(db_session)
            writer.start()
        except Exception:
            pytest.fail("worker raised exception")

        # activity = query.get_activity_by_key(message_id)
        # assert activity.status == ActivityStatus.PROCESSED

    def test_command(self, monkeypatch):
        monkeypatch.setenv("MONITORING", "FALSE")
        from apihub.result import ResultWriter

        try:
            writer = ResultWriter()
            writer.parse_args(
                "--in-kind FILE --in-filename tests/fixtures/command_input.txt".split()
            )
            writer.start()
        except Exception:
            pytest.fail("worker raised exception")
