import pytest
from datetime import datetime
import factory
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apihub.common.db_session import create_session
from apihub.subscription.router import router
from apihub.subscription.models import SubscriptionTier
from apihub.activity.models import Activity
from apihub.activity.queries import ActivityQuery, ActivityException
from apihub.activity.schemas import ActivityCreate, ActivityStatus


class ActivityFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Activity

    id = factory.Sequence(int)
    created_at = factory.LazyFunction(datetime.now)
    request = factory.Sequence(lambda n: f"app{n}")
    username = factory.Sequence(lambda n: f"tester{n}")
    tier = SubscriptionTier.TRIAL
    status = ActivityStatus.PROCESSED
    request_key = factory.Sequence(lambda n: f"request_key{n}")
    result = ""
    payload = ""
    ip_address = ""
    latency = 0.0


@pytest.fixture(scope="function")
def client(db_session):
    def _create_session():
        try:
            yield db_session
        finally:
            pass

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[create_session] = _create_session
    ActivityFactory._meta.sqlalchemy_session = db_session
    ActivityFactory._meta.sqlalchemy_session_persistence = "commit"
    ActivityFactory(
        username="tester",
        request="async/app1",
        request_key="app1_key",
        status=ActivityStatus.PROCESSED,
    )
    yield TestClient(app)


@pytest.fixture(scope="function")
def query(db_session):
    yield ActivityQuery(db_session)


class TestActivity:
    def test_create_activity(self, query):
        query.create_activity(
            ActivityCreate(
                request="async/test",
                username="ahmed",
                tier=SubscriptionTier.TRIAL,
                status=ActivityStatus.ACCEPTED,
                request_key="async/test_key1234",
                result="",
                payload="",
                ip_address="",
                latency=0.0,
            )
        )

        assert (
            query.get_activity_by_key("async/test_key1234").request_key == "async/test_key1234"
        )

    def test_get_activity_by_key(self, client, query):
        assert query.get_activity_by_key("app1_key").request_key == "app1_key"

        with pytest.raises(ActivityException):
            query.get_activity_by_key("key 2")

    def test_update_activity(self, client, query):
        activity = query.get_activity_by_key("app1_key")
        assert activity.tier == SubscriptionTier.TRIAL

        query.update_activity(
            "app1_key",
            **{"tier": SubscriptionTier.STANDARD, "ip_address": "test ip"},
        )

        activity = query.get_activity_by_key("app1_key")
        assert (
            activity.tier == SubscriptionTier.STANDARD
            and activity.ip_address == "test ip"
            and activity.latency > 0.0
        )

        with pytest.raises(ActivityException):
            query.update_activity(
                "not existing",
                **{"tier": SubscriptionTier.STANDARD, "ip_address": "test ip"},
            )
