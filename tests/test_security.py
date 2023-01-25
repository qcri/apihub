from operator import itemgetter
from datetime import datetime
from base64 import b64encode

import pytest
import factory
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException

from apihub.common.db_session import create_session
from apihub.security.models import User
from apihub.security.queries import UserQuery
from apihub.security.schemas import UserCreate, UserType, UserRegister, SecurityToken
from apihub.security.router import router
from apihub.security.depends import require_admin
from apihub.security.helpers import hash_password


SALT = b64encode(
    b"<\x9c\x8a\x0c\xd6$\xa31\x9c(\xfe\x94k\\(\xd8\xbdw\xd4P\xb8\xf6]\x9cY\x83\x91\x18\xfc!\x9dv"
).decode("ascii")


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = User

    id = factory.Sequence(int)
    name = factory.Sequence(lambda n: f"Mr. Tester{n}")
    email = factory.Sequence(lambda n: f"tester{n}@tester.com")
    salt = SALT
    hashed_password = itemgetter(1)(hash_password("password", salt=SALT))
    role = UserType.USER
    created_at = factory.LazyFunction(datetime.now)


def test_user_create(db_session):
    query = UserQuery(db_session)
    query.create_user(
        user=UserCreate(
            name="Mr. Tester",
            email="newuser@test.com",
            password="testpassword",
            role=UserType.USER,
        )
    )

    user = query.get_user_by_email(email="newuser@test.com")
    assert user is not None

    another_user = query.get_user_by_id(user_id=user.id)
    assert user.email == another_user.email


@pytest.fixture(scope="function")
def client(db_session):
    def _create_session():
        try:
            yield db_session
        finally:
            pass

    app = FastAPI()
    app.include_router(router)

    @app.exception_handler(AuthJWTException)
    def authjwt_exception_handler(request: Request, exc: AuthJWTException):
        return JSONResponse(
            status_code=exc.status_code, content={"detail": exc.message}
        )

    @app.get("/protected")
    def protected(Authorize: AuthJWT = Depends()):
        Authorize.jwt_required()

        user = Authorize.get_jwt_subject()
        role = Authorize.get_raw_jwt()["role"]
        return {"user": user, "role": role}

    @app.get("/admin")
    def admin(email=Depends(require_admin)):
        return email

    app.dependency_overrides[create_session] = _create_session

    UserFactory._meta.sqlalchemy_session = db_session
    UserFactory._meta.sqlalchemy_session_persistence = "commit"

    UserFactory(email="tester@test.com", role=UserType.USER)
    UserFactory(email="admin@test.com", role=UserType.ADMIN)
    UserFactory(email="publisher@test.com", role=UserType.PUBLISHER)
    UserFactory(email="user@test.com", role=UserType.USER)
    UserFactory(email="app@test.com", role=UserType.APP)

    yield TestClient(app)


class TestAuthenticate:
    def _make_auth_header(self, email, password):
        from base64 import b64encode

        raw = b64encode(f"{email}:{password}".encode("ascii")).decode("ascii")
        return {"Authorization": f"Basic {raw}"}

    def test_authenticate_wrong_user(self, client):
        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("nosuchuser@test.com", "password"),
        )
        assert response.status_code == 403

    def test_authenticate_wrong_password(self, client):
        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("tester@test.com", "nosuchpassword"),
        )
        assert response.status_code == 403

    def test_authenticate(self, client):
        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("tester@test.com", "password"),
            params={"expires_days": 2},
        )
        assert response.status_code == 200
        assert SecurityToken.parse_obj(response.json()).access_token is not None

    def test_pretected_no_token(self, client):
        response = client.get(
            "/protected",
        )
        assert response.status_code == 401

    def test_token(self, client):
        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("tester@test.com", "password"),
        )
        assert response.status_code == 200
        auth_response = SecurityToken.parse_obj(response.json())
        token = auth_response.access_token
        response = client.get(
            "/protected", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

    def test_require_admin_when_admin(self, client):
        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("admin@test.com", "password"),
        )
        assert response.status_code == 200
        auth_response = SecurityToken.parse_obj(response.json())
        token = auth_response.access_token
        response = client.get("/admin", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200

    def test_require_admin_when_manager(self, client):
        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("publisher@test.com", "password"),
        )
        assert response.status_code == 200
        auth_response = SecurityToken.parse_obj(response.json())
        token = auth_response.access_token
        response = client.get("/admin", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403

    def test_create_and_get_user(self, client):
        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("admin@test.com", "password"),
        )
        assert response.status_code == 200
        auth_response = SecurityToken.parse_obj(response.json())
        token = auth_response.access_token

        response = client.get("/user", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json().get("email") == "admin@test.com"

        new_user = UserCreate(
            name="New User",
            email="newuser@test.com",
            password="password",
            role="user",
        )
        response = client.post(
            f"/user",
            headers={"Authorization": f"Bearer {token}"},
            json=new_user.dict(),
        )
        assert response.status_code == 200
        
        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("newuser@test.com", "password"),
        )
        assert response.status_code == 200
        auth_response = SecurityToken.parse_obj(response.json())
        token = auth_response.access_token

        response = client.get(
            f"/user", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json().get("email") == new_user.email

    def test_get_users(self, client):
        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("admin@test.com", "password"),
        )
        assert response.status_code == 200
        auth_response = SecurityToken.parse_obj(response.json())
        token = auth_response.access_token

        response = client.get(
            "/user",
            headers={"Authorization": f"Bearer {token}"},
            json={"emails": "admin@test.com,publisher@test.com,user@test.com"},
        )
        assert response.status_code == 200
        assert len(response.json()) == 3

    def test_list_users(self, client):
        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("admin@test.com", "password"),
        )
        assert response.status_code == 200
        auth_response = SecurityToken.parse_obj(response.json())
        token = auth_response.access_token

        response = client.get(
            "/users/admin",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_change_password_user(self, client):
        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("user@test.com", "password"),
        )
        assert response.status_code == 200
        auth_response = SecurityToken.parse_obj(response.json())
        token = auth_response.access_token

        response = client.post(
            "/user/_password",
            headers={"Authorization": f"Bearer {token}"},
            json={"password": "newpassword"},
        )
        assert response.status_code == 200

        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("user@test.com", "password"),
        )
        assert response.status_code == 403

        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("user@test.com", "newpassword"),
        )
        assert response.status_code == 200

        response = client.post(
            "/user/_password",
            headers={"Authorization": f"Bearer {token}"},
            json={"password": "password"},
        )
        assert response.status_code == 200

    def test_change_password_admin(self, client):
        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("admin@test.com", "password"),
        )
        assert response.status_code == 200
        auth_response = SecurityToken.parse_obj(response.json())
        token = auth_response.access_token

        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("user@test.com", "password"),
        )
        assert response.status_code == 200

        response = client.post(
            "/user/user@test.com/_password",
            headers={"Authorization": f"Bearer {token}"},
            json={"password": "newpassword"},
        )
        assert response.status_code == 200

        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("user@test.com", "password"),
        )
        assert response.status_code == 403

        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("user@test.com", "newpassword"),
        )
        assert response.status_code == 200

        response = client.post(
            "/user/user@test.com/_password",
            headers={"Authorization": f"Bearer {token}"},
            json={"password": "password"},
        )
        assert response.status_code == 200

    def test_register(self, client):
        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("app@test.com", "password"),
        )
        assert response.status_code == 200
        auth_response = SecurityToken.parse_obj(response.json())
        token = auth_response.access_token

        new_user = UserRegister(
            name="New User",
            email="newuser@test.com",
            password="password",
        )
        response = client.post(
            "/register",
            headers={"Authorization": f"Bearer {token}"},
            json=new_user.dict(),
        )
        assert response.status_code == 200

        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("newuser@test.com", "password"),
        )
        assert response.status_code == 200
        auth_response = SecurityToken.parse_obj(response.json())
        token = auth_response.access_token

        response = client.get("/user", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json().get("email") == new_user.email
