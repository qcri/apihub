from datetime import datetime, timedelta

import pytest
import factory
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apihub.common.db_session import create_session
from apihub.security.schemas import UserBase, UserType
from apihub.security.depends import require_user, require_admin, require_token
from apihub.subscription.models import Subscription
from apihub.subscription.router import router, SubscriptionIn


class SubscriptionFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Subscription

    id = factory.Sequence(int)
    username = factory.Sequence(lambda n: f"tester{n}")
    application = "test"
    limit = 100
    starts_at = factory.LazyFunction(datetime.now)
    expires_at = factory.LazyFunction(lambda: datetime.now() + timedelta(days=1))
    recurring = False
    created_at = factory.LazyFunction(datetime.now)
    created_by = "admin"
    notes = None


@pytest.fixture(scope="function")
def client(db_session):
    def _create_session():
        try:
            yield db_session
        finally:
            pass

    def _require_admin():
        return "admin"

    def _require_user():
        return "user"

    def _require_token():
        return UserBase(username="tester", role=UserType.ADMIN)

    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[create_session] = _create_session
    app.dependency_overrides[require_admin] = _require_admin
    app.dependency_overrides[require_user] = _require_user
    app.dependency_overrides[require_token] = _require_token

    SubscriptionFactory._meta.sqlalchemy_session = db_session
    SubscriptionFactory._meta.sqlalchemy_session_persistence = "commit"

    SubscriptionFactory(username="user", application="app", limit=1000)

    yield TestClient(app)


class TestApplication:
    def test_create_and_get_subscription(self, client):
        new_subscription = SubscriptionIn(
            username="tester",
            application="application",
            limit=123,
            expires_at=None,
            recurring=False,
        )
        response = client.post(
            "/subscription",
            data=new_subscription.json(),
        )
        assert response.status_code == 200

        response = client.get(
            "/subscription/application",
        )
        assert response.status_code == 200
        assert response.json().get("limit") == 123

    def test_get_application_token(self, client):
        response = client.get(
            "/token/app",
        )
        assert response.status_code == 200
        assert response.json().get("token") is not None
