from datetime import datetime, timedelta
from operator import itemgetter
from base64 import b64encode

import pytest
import factory
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from apihub.common.db_session import create_session
from apihub.security.models import User
from apihub.security.schemas import UserBase, UserType
from apihub.security.depends import require_user, require_admin, require_token
from apihub.subscription.depends import (
    require_subscription_balance,
)
from apihub.subscription.models import (
    Subscription,
    SubscriptionTier,
    Application,
    SubscriptionPricing,
)
from apihub.subscription.router import router
from apihub.subscription.schemas import (
    SubscriptionIn,
    ApplicationCreate,
    SubscriptionPricingBase,
)

from apihub.security.helpers import hash_password

SALT = b64encode(
    b"<\x9c\x8a\x0c\xd6$\xa31\x9c(\xfe\x94k\\(\xd8\xbdw\xd4P\xb8\xf6]\x9cY\x83\x91\x18\xfc!\x9dv"
).decode("ascii")


class ApplicationFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Application

    id = factory.Sequence(int)
    name = factory.Sequence(lambda n: f"app {n}")
    url = factory.Sequence(lambda n: f"app/{n}")
    description = "description"


class SubscriptionPricingFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = SubscriptionPricing

    id = factory.Sequence(int)
    tier = SubscriptionTier.TRIAL
    price = 100.0
    credit = 100.0
    application = factory.Sequence(lambda n: f"app{n}")


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = User

    id = factory.Sequence(int)
    username = factory.Sequence(lambda n: f"tester{n}")
    salt = SALT
    hashed_password = itemgetter(1)(hash_password("password", salt=SALT))
    role = UserType.USER
    created_at = factory.LazyFunction(datetime.now)


class SubscriptionFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Subscription

    id = factory.Sequence(int)
    username = factory.Sequence(lambda n: f"tester{n}")
    application = "test"
    active = True
    tier = SubscriptionTier.TRIAL
    credit = 100
    balance = 0
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

    def _require_admin_token():
        return UserBase(username="tester", role=UserType.ADMIN)

    def _require_user_token():
        return UserBase(username="tester", role=UserType.USER)

    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[create_session] = _create_session
    app.dependency_overrides[require_admin] = _require_admin
    app.dependency_overrides[require_user] = _require_user
    app.dependency_overrides[require_token] = _require_user_token

    @app.get("/api_balance/{application}")
    def api_function_2(
        application: str, username: str = Depends(require_subscription_balance)
    ):
        pass

    UserFactory._meta.sqlalchemy_session = db_session
    UserFactory._meta.sqlalchemy_session_persistence = "commit"
    UserFactory(username="tester", role=UserType.USER)

    ApplicationFactory._meta.sqlalchemy_session = db_session
    ApplicationFactory._meta.sqlalchemy_session_persistence = "commit"
    application = ApplicationFactory(name="test", url="/test")

    SubscriptionPricingFactory._meta.sqlalchemy_session = db_session
    SubscriptionPricingFactory._meta.sqlalchemy_session_persistence = "commit"
    pricing = SubscriptionPricingFactory(
        tier=SubscriptionTier.TRIAL,
        price=100,
        credit=100,
        application="test",
    )

    SubscriptionFactory._meta.sqlalchemy_session = db_session
    SubscriptionFactory._meta.sqlalchemy_session_persistence = "commit"

    SubscriptionFactory(username="tester", application="test", credit=100)

    yield TestClient(app)


def _require_admin_token():
    return UserBase(username="tester", role=UserType.ADMIN)


def _require_user_token():
    return UserBase(username="tester", role=UserType.USER)


class TestApplication:
    def test_create_application(self, client):
        new_application = ApplicationCreate(
            name="app",
            url="/test",
            description="test",
            pricing=[
                SubscriptionPricingBase(
                    tier=SubscriptionTier.TRIAL, price=100, credit=100
                ),
                SubscriptionPricingBase(
                    tier=SubscriptionTier.STANDARD, price=200, credit=200
                ),
                SubscriptionPricingBase(
                    tier=SubscriptionTier.PREMIUM, price=300, credit=300
                ),
            ],
        )
        response = client.post(
            "/application",
            data=new_application.json(),
        )
        assert response.status_code == 200

        response = client.get(
            "/application/app",
        )

        response_json = response.json()
        assert len(response_json["pricing"]) == 3

    def test_list_application(self, client, db_session):
        response = client.get("/application")
        assert response.status_code == 200
        response_json = response.json()
        assert len(response_json) == 1

    def test_get_application(self, client, db_session):
        response = client.get(
            "/application/test",
        )
        assert response.status_code == 200
        response_json = response.json()
        assert (
            len(response_json["pricing"]) == 1
            and response_json["pricing"][0]["tier"] == "TRIAL"
        )


class TestSubscription:
    def test_create_and_get_subscription(self, client, db_session):
        ApplicationFactory._meta.sqlalchemy_session = db_session
        ApplicationFactory._meta.sqlalchemy_session_persistence = "commit"
        ApplicationFactory(name="application", url="/test")

        SubscriptionPricingFactory._meta.sqlalchemy_session = db_session
        SubscriptionPricingFactory._meta.sqlalchemy_session_persistence = "commit"
        SubscriptionPricingFactory(
            tier=SubscriptionTier.TRIAL,
            price=100,
            credit=100,
            application="application",
        )

        # case 1: create subscription
        new_subscription = SubscriptionIn(
            username="tester",
            application="application",
            tier=SubscriptionTier.TRIAL,
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
        assert response.json().get("credit") == 100
        assert response.json().get("active") is True

    def test_get_all_subscriptions(self, client):
        response = client.get(
            "/subscription",
        )
        assert response.status_code == 200
        response_json = response.json()
        assert len(response_json) == 1

    def test_create_subscription_not_existing_user(self, client):
        new_subscription = SubscriptionIn(
            username="not existing user",
            application="app 1",
            tier=SubscriptionTier.TRIAL,
            expires_at=None,
            recurring=False,
        )
        response = client.post(
            "/subscription",
            data=new_subscription.json(),
        )
        assert response.status_code == 401

    def test_get_application_token(self, client, db_session):
        SubscriptionFactory._meta.sqlalchemy_session = db_session
        SubscriptionFactory._meta.sqlalchemy_session_persistence = "commit"

        ApplicationFactory(name="app")
        SubscriptionPricingFactory(
            tier=SubscriptionTier.TRIAL, price=100, credit=100, application="app"
        )
        SubscriptionFactory(username="tester", application="app", credit=100)

        response = client.get(
            "/token/app",
        )
        assert response.status_code == 200, response.json()
        assert response.json().get("token") is not None

        ApplicationFactory(name="app_2")
        SubscriptionPricingFactory(
            tier=SubscriptionTier.TRIAL, price=100, credit=100, application="app_2"
        )
        SubscriptionFactory(
            username="tester", application="app_2", active=False, credit=1000
        )

        response = client.get(
            "/subscription/app_2",
        )

        assert response.status_code == 400, response.json()

    def test_get_application_token_admin(self, client, db_session):
        client.app.dependency_overrides[require_token] = _require_admin_token
        SubscriptionFactory._meta.sqlalchemy_session = db_session
        SubscriptionFactory._meta.sqlalchemy_session_persistence = "commit"

        ApplicationFactory(name="app2")
        SubscriptionPricingFactory(
            tier=SubscriptionTier.TRIAL, price=100, credit=100, application="app2"
        )
        SubscriptionFactory(username="tester", application="app2", credit=1000)

        response = client.get(
            "/token/app2",
            params={
                "username": "tester",
                "expires_days": 30,
            },
        )
        client.app.dependency_overrides[require_token] = _require_user_token
        assert response.status_code == 200, response.json()
        assert response.json().get("token") is not None

    def test_create_duplicate_subscription(self, client, db_session):
        new_subscription = SubscriptionIn(
            username="tester",
            application="application",
            tier=SubscriptionTier.TRIAL,
            expires_at=None,
            recurring=False,
        )
        response = client.post(
            "/subscription",
            data=new_subscription.json(),
        )
        assert response.status_code == 404

        ApplicationFactory._meta.sqlalchemy_session = db_session
        ApplicationFactory._meta.sqlalchemy_session_persistence = "commit"
        ApplicationFactory(name="application", url="/test")

        SubscriptionPricingFactory._meta.sqlalchemy_session = db_session
        SubscriptionPricingFactory._meta.sqlalchemy_session_persistence = "commit"
        SubscriptionPricingFactory(
            tier=SubscriptionTier.TRIAL,
            price=100,
            credit=100,
            application="application",
        )

        new_subscription = SubscriptionIn(
            username="tester",
            application="application",
            tier=SubscriptionTier.TRIAL,
            expires_at=None,
            recurring=False,
        )
        response = client.post(
            "/subscription",
            data=new_subscription.json(),
        )
        assert response.status_code == 200, response.json()

        response = client.post(
            "/subscription",
            data=new_subscription.json(),
        )
        assert response.status_code == 403, response.json()

    def test_require_balance(self, client, db_session):
        SubscriptionFactory._meta.sqlalchemy_session = db_session
        SubscriptionFactory._meta.sqlalchemy_session_persistence = "commit"

        ApplicationFactory(name="app3")
        SubscriptionPricingFactory(
            tier=SubscriptionTier.TRIAL, price=100, credit=100, application="app3"
        )
        SubscriptionFactory(
            username="tester",
            application="app3",
            tier=SubscriptionTier.TRIAL,
            credit=2,
        )

        response = client.get(
            "/token/app3",
        )
        assert response.status_code == 200, response.json()
        token = response.json().get("token")

        response = client.get(
            "/api_balance/app3", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, response.json()
