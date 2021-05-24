from base64 import b64encode
from datetime import datetime
from operator import itemgetter

import pytest
import factory
from fastapi.testclient import TestClient

from apihub.common.db_session import create_session
from apihub.security.schemas import UserType
from apihub.security.models import User
from apihub.security.helpers import hash_password
from apihub.subscription.depends import require_subscription


SALT = b64encode(
    b"<\x9c\x8a\x0c\xd6$\xa31\x9c(\xfe\x94k\\(\xd8\xbdw\xd4P\xb8\xf6]\x9cY\x83\x91\x18\xfc!\x9dv"
).decode("ascii")


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = User

    id = factory.Sequence(int)
    username = factory.Sequence(lambda n: f"tester{n}")
    salt = SALT
    hashed_password = itemgetter(1)(hash_password("password", salt=SALT))
    role = UserType.USER
    created_at = factory.LazyFunction(datetime.now)


@pytest.fixture(scope="function")
def client(db_session, monkeypatch):
    def _create_session():
        try:
            yield db_session
        finally:
            pass

    def _ip_rate_limited():
        pass

    def _require_subscription():
        return "user"

    monkeypatch.setenv("IN_KIND", "LREDIS")
    monkeypatch.setenv("OUT_KIND", "LREDIS")
    from apihub.server import api, ip_rate_limited

    api.dependency_overrides[create_session] = _create_session
    api.dependency_overrides[ip_rate_limited] = _ip_rate_limited
    api.dependency_overrides[require_subscription] = _require_subscription

    UserFactory._meta.sqlalchemy_session = db_session
    UserFactory._meta.sqlalchemy_session_persistence = "commit"

    UserFactory(username="tester", role=UserType.USER)
    UserFactory(username="admin", role=UserType.ADMIN)
    UserFactory(username="manager", role=UserType.MANAGER)
    UserFactory(username="user", role=UserType.USER)

    yield TestClient(api)


def test_slash(client):
    status_codes = []
    for i in range(20):
        response = client.get("/")
        status_codes.append(response.status_code)
    assert len(status_codes) == 20
    # assert len(list(filter(lambda x: x == 200, status_codes))) == 10


def test_async_service(client):
    response = client.post(
        "/async/test",
        params={"text": "this is simple"},
    )
    assert response.status_code == 200
