from datetime import datetime, timedelta
from operator import itemgetter
from base64 import b64encode

import pytest
import factory
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from apihub.common.db_session import create_session
from apihub.security.models import User
from apihub.security.schemas import UserBase, UserType, UserBaseWithId
from apihub.security.depends import require_user, require_admin, require_token, require_publisher, require_logged_in
from apihub.subscription.depends import (
    require_subscription_balance,
    SubscriptionToken,
)
from apihub.subscription.models import (
    Subscription,
    SubscriptionTier,
    Application,
    Pricing,
)
from apihub.subscription.router import router
from apihub.subscription.schemas import (
    SubscriptionIn,
    ApplicationCreate,
    PricingBase,
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

    created_at = factory.LazyFunction(datetime.now)
    user_id = factory.Sequence(int)


class PricingFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Pricing

    id = factory.Sequence(int)
    tier = SubscriptionTier.TRIAL
    price = 100.0
    credit = 100.0
    application_id = factory.Sequence(int)


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = User

    id = factory.Sequence(int)
    name = factory.Sequence(lambda n: f"Mr Tester{n}")
    email = factory.Sequence(lambda n: f"tester{n}@test.com")
    salt = SALT
    hashed_password = itemgetter(1)(hash_password("password", salt=SALT))
    role = UserType.USER
    created_at = factory.LazyFunction(datetime.now)


class SubscriptionFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Subscription

    id = factory.Sequence(int)
    is_active = True
    tier = SubscriptionTier.TRIAL
    credit = 100
    balance = 0
    starts_at = factory.LazyFunction(datetime.now)
    expires_at = factory.LazyFunction(lambda: datetime.now() + timedelta(days=1))
    recurring = False
    created_at = factory.LazyFunction(datetime.now)
    # created_by = "admin"
    notes = None

    user_id = factory.Sequence(int)
    application_id = factory.Sequence(int)
    pricing_id = factory.Sequence(int)


def _require_admin_token():
    return UserBaseWithId(id=1, email="tester", name="tester", role=UserType.ADMIN)


def _require_user_token():
    return UserBaseWithId(id=1, email="tester", name="tester", role=UserType.USER)


def _require_publisher_token():
    return UserBaseWithId(id=1, email="tester", name="tester", role=UserType.PUBLISHER)


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
    app.dependency_overrides[require_admin] = _require_admin_token
    app.dependency_overrides[require_user] = _require_user_token
    app.dependency_overrides[require_publisher] = _require_publisher_token
    app.dependency_overrides[require_token] = _require_user_token
    app.dependency_overrides[require_logged_in] = _require_user_token

    @app.get("/api_balance/{application}")
    def api_function_2(
        application: str, subscription: SubscriptionToken = Depends(require_subscription_balance)
    ):
        pass

    UserFactory._meta.sqlalchemy_session = db_session
    UserFactory._meta.sqlalchemy_session_persistence = "commit"
    tester = UserFactory(id=100, email="tester@test.com", role=UserType.USER)

    UserFactory._meta.sqlalchemy_session = db_session
    UserFactory._meta.sqlalchemy_session_persistence = "commit"
    publisher = UserFactory(id=200, email="publisher@test.com", role=UserType.PUBLISHER)

    ApplicationFactory._meta.sqlalchemy_session = db_session
    ApplicationFactory._meta.sqlalchemy_session_persistence = "commit"
    application = ApplicationFactory(id=100, name="test", url="/test", user_id=publisher.id)

    PricingFactory._meta.sqlalchemy_session = db_session
    PricingFactory._meta.sqlalchemy_session_persistence = "commit"
    pricing = PricingFactory(
        id=100,
        tier=SubscriptionTier.TRIAL,
        price=100,
        credit=100,
        application_id=application.id,
    )

    SubscriptionFactory._meta.sqlalchemy_session = db_session
    SubscriptionFactory._meta.sqlalchemy_session_persistence = "commit"
    SubscriptionFactory(user_id=tester.id, application_id=application.id, credit=100, pricing=pricing)

    yield TestClient(app)


class TestApplication:
    def test_create_application(self, client):
        new_application = ApplicationCreate(
            name="app",
            url="/test",
            description="test",
            pricings=[
                PricingBase(
                    tier=SubscriptionTier.TRIAL, price=100, credit=100
                ),
                PricingBase(
                    tier=SubscriptionTier.STANDARD, price=200, credit=200
                ),
                PricingBase(
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
        assert len(response_json["pricings"]) == 3

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
            len(response_json["pricings"]) == 1
            and response_json["pricings"][0]["tier"] == "TRIAL"
        )


class TestSubscription:
    def test_create_and_get_subscription(self, client, db_session):
        UserFactory._meta.sqlalchemy_session = db_session
        UserFactory._meta.sqlalchemy_session_persistence = "commit"
        publisher = UserFactory(email="publisher1@test.com", role=UserType.PUBLISHER)

        ApplicationFactory._meta.sqlalchemy_session = db_session
        ApplicationFactory._meta.sqlalchemy_session_persistence = "commit"
        application = ApplicationFactory(name="application", url="/test", user_id=publisher.id)

        PricingFactory._meta.sqlalchemy_session = db_session
        PricingFactory._meta.sqlalchemy_session_persistence = "commit"
        pricing = PricingFactory(
            tier=SubscriptionTier.TRIAL,
            price=100,
            credit=100,
        )

        # case 1: create subscription
        new_subscription = SubscriptionIn(
            user_id=publisher.id,
            application_id=application.id,
            pricing_id=pricing.id,
            tier=SubscriptionTier.TRIAL,
            expires_at=None,
            recurring=False,
        )
        response = client.post(
            "/subscription",
            data=new_subscription.json(),
        )
        assert response.status_code == 200

        def _require_logged_in():
            return publisher

        client.app.dependency_overrides[require_logged_in] = _require_logged_in

        response = client.get(
            f"/subscription/{application.id}",
        )
        assert response.status_code == 200
        assert response.json().get("credit") == 100

    def test_get_all_subscriptions(self, client):

        def _require_user():
            return UserBaseWithId(id=100, email="", name="", role=UserType.USER)

        client.app.dependency_overrides[require_user] = _require_user

        response = client.get(
            "/subscription",
        )
        assert response.status_code == 200
        response_json = response.json()
        assert len(response_json) == 1

    def test_create_subscription_not_existing_user(self, client):
        new_subscription = SubscriptionIn(
            user_id=-1,
            application_id=1,
            pricing_id=1,
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
        def _require_user():
            return UserBaseWithId(id=100, email="", name="", role=UserType.USER)

        client.app.dependency_overrides[require_user] = _require_user

        SubscriptionFactory._meta.sqlalchemy_session = db_session
        SubscriptionFactory._meta.sqlalchemy_session_persistence = "commit"

        application = ApplicationFactory(name="app", user_id=100)
        pricing = PricingFactory(
            tier=SubscriptionTier.TRIAL, price=100, credit=100, application_id=application.id
        )
        SubscriptionFactory(user_id=100, application_id=application.id, pricing_id=pricing.id, credit=100)

        response = client.get(
            "/token/app",
        )
        assert response.status_code == 200, response.json()
        assert response.json().get("access_token") is not None

    def test_create_duplicate_subscription(self, client, db_session):
        new_subscription = SubscriptionIn(
            user_id=100,
            application_id=100,
            pricing_id=100,
            tier=SubscriptionTier.TRIAL,
            expires_at=None,
            recurring=False,
        )
        response = client.post(
            "/subscription",
            data=new_subscription.json(),
        )
        assert response.status_code == 403

    def test_require_balance(self, client, db_session):
        def _require_user():
            return UserBaseWithId(id=100, email="", name="", role=UserType.USER)

        client.app.dependency_overrides[require_user] = _require_user

        SubscriptionFactory._meta.sqlalchemy_session = db_session
        SubscriptionFactory._meta.sqlalchemy_session_persistence = "commit"

        response = client.get(
            "/token/test",
        )
        assert response.status_code == 200, response.json()
        token = response.json().get("access_token")

        response = client.get(
            "/api_balance/test", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, response.json()