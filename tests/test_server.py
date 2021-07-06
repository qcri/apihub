import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from apihub_users.common.db_session import create_session
from apihub_users.subscription.depends import require_subscription


@pytest.fixture(scope="function")
def client(monkeypatch):
    def _create_session():
        pass

    def _ip_rate_limited():
        pass

    def _require_subscription():
        return "user"

    def _record_usage(username, application, redis):
        pass

    monkeypatch.setenv("OUT_KIND", "MEM")

    from apihub.server import api, ip_rate_limited

    api.dependency_overrides[create_session] = _create_session
    api.dependency_overrides[ip_rate_limited] = _ip_rate_limited
    api.dependency_overrides[require_subscription] = _require_subscription

    yield TestClient(api)


def test_slash(client):
    status_codes = []
    for i in range(20):
        response = client.get("/")
        status_codes.append(response.status_code)
    assert len(status_codes) == 20
    # assert len(list(filter(lambda x: x == 200, status_codes))) == 10


def test_async_service_json(client, monkeypatch):
    class Input(BaseModel):
        text: str
        probability: float

    def _get_app_input_schema(application, redis=None):
        return Input.schema()

    import apihub.server

    monkeypatch.setattr(apihub.server, "get_app_input_schema", _get_app_input_schema)

    response = client.post(
        "/async/test", params={"text": "this is simple"}, json={"probability": 0.6}
    )
    assert response.status_code == 200


def test_define_service(client):
    response = client.get(
        "/define/test",
    )
    assert response.status_code == 200
