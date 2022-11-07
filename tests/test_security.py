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
from apihub.security.schemas import UserCreate, UserType, UserRegister
from apihub.security.router import router, AuthenticateResponse
from apihub.security.depends import require_admin
from apihub.security.helpers import hash_password


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


def test_user_create(db_session):
    query = UserQuery(db_session)
    query.create_user(
        user=UserCreate(
            username="tester",
            email="newuser@test.com",
            password="testpassword",
            role=UserType.USER,
        )
    )

    user = query.get_user_by_username(username="tester")
    assert user is not None

    another_user = query.get_user_by_id(user_id=user.id)
    assert user.username == another_user.username


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
        roles = Authorize.get_raw_jwt()["roles"]
        return {"user": user, "roles": roles}

    @app.get("/admin")
    def admin(username=Depends(require_admin)):
        return username

    app.dependency_overrides[create_session] = _create_session

    UserFactory._meta.sqlalchemy_session = db_session
    UserFactory._meta.sqlalchemy_session_persistence = "commit"

    UserFactory(username="tester", role=UserType.USER)
    UserFactory(username="admin", role=UserType.ADMIN)
    UserFactory(username="manager", role=UserType.MANAGER)
    UserFactory(username="user", role=UserType.USER)
    UserFactory(username="app", role=UserType.APP)

    yield TestClient(app)


class TestAuthenticate:
    def _make_auth_header(self, username, password):
        from base64 import b64encode

        raw = b64encode(f"{username}:{password}".encode("ascii")).decode("ascii")
        return {"Authorization": f"Basic {raw}"}

    def test_authenticate_wrong_user(self, client):
        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("nosuchuser", "password"),
        )
        assert response.status_code == 403

    def test_authenticate_wrong_password(self, client):
        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("tester", "nosuchpassword"),
        )
        assert response.status_code == 403

    def test_authenticate(self, client):
        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("tester", "password"),
            params={"expires_days": 2},
        )
        assert response.status_code == 200
        assert AuthenticateResponse.parse_obj(response.json())

    def test_pretected_no_token(self, client):
        response = client.get(
            "/protected",
        )
        assert response.status_code == 401

    def test_token(self, client):
        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("tester", "password"),
        )
        assert response.status_code == 200
        auth_response = AuthenticateResponse.parse_obj(response.json())
        token = auth_response.access_token
        response = client.get(
            "/protected", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

    def test_require_admin_when_admin(self, client):
        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("manager", "password"),
        )
        assert response.status_code == 200
        auth_response = AuthenticateResponse.parse_obj(response.json())
        token = auth_response.access_token
        response = client.get("/admin", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403

    def test_require_admin_when_manager(self, client):
        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("admin", "password"),
        )
        assert response.status_code == 200
        auth_response = AuthenticateResponse.parse_obj(response.json())
        token = auth_response.access_token
        response = client.get("/admin", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200

    def test_create_and_get_user(self, client):
        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("admin", "password"),
        )
        assert response.status_code == 200
        auth_response = AuthenticateResponse.parse_obj(response.json())
        token = auth_response.access_token

        response = client.get("/user/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json().get("username") == "admin"

        response = client.get(
            "/user/user", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json().get("username") == "user"

        new_user = UserCreate(
            username="newuser",
            email="newuser@test.com",
            password="password",
            role="user",
        )
        response = client.post(
            f"/user/{new_user.username}",
            headers={"Authorization": f"Bearer {token}"},
            json=new_user.dict(),
        )
        assert response.status_code == 200

        response = client.get(
            f"/user/{new_user.username}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json().get("username") == new_user.username

    def test_get_users(self, client):
        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("admin", "password"),
        )
        assert response.status_code == 200
        auth_response = AuthenticateResponse.parse_obj(response.json())
        token = auth_response.access_token

        response = client.get(
            "/user",
            headers={"Authorization": f"Bearer {token}"},
            json={"usernames": "admin,manager,user"},
        )
        assert response.status_code == 200
        assert len(response.json()) == 3

    def test_list_users(self, client):
        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("admin", "password"),
        )
        assert response.status_code == 200
        auth_response = AuthenticateResponse.parse_obj(response.json())
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
            headers=self._make_auth_header("user", "password"),
        )
        assert response.status_code == 200
        auth_response = AuthenticateResponse.parse_obj(response.json())
        token = auth_response.access_token

        response = client.post(
            "/user/_password",
            headers={"Authorization": f"Bearer {token}"},
            json={"password": "newpassword"},
        )
        assert response.status_code == 200

        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("user", "password"),
        )
        assert response.status_code == 403

        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("user", "newpassword"),
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
            headers=self._make_auth_header("admin", "password"),
        )
        assert response.status_code == 200
        auth_response = AuthenticateResponse.parse_obj(response.json())
        token = auth_response.access_token

        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("user", "password"),
        )
        assert response.status_code == 200

        response = client.post(
            "/user/user/_password",
            headers={"Authorization": f"Bearer {token}"},
            json={"password": "newpassword"},
        )
        assert response.status_code == 200

        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("user", "password"),
        )
        assert response.status_code == 403

        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("user", "newpassword"),
        )
        assert response.status_code == 200

        response = client.post(
            "/user/user/_password",
            headers={"Authorization": f"Bearer {token}"},
            json={"password": "password"},
        )
        assert response.status_code == 200

    def test_register(self, client):
        response = client.get(
            "/_authenticate",
            headers=self._make_auth_header("app", "password"),
        )
        assert response.status_code == 200
        auth_response = AuthenticateResponse.parse_obj(response.json())
        token = auth_response.access_token

        new_user = UserRegister(
            username="newuser",
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
            headers=self._make_auth_header("newuser", "password"),
        )
        assert response.status_code == 200
        auth_response = AuthenticateResponse.parse_obj(response.json())
        token = auth_response.access_token

        response = client.get("/user/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json().get("username") == new_user.username
