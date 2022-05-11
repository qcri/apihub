from unittest import mock

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import Dict, Any

from apihub_users.common.db_session import create_session
from apihub_users.subscription.depends import require_subscription
from apihub.utils import make_topic


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
    monkeypatch.setenv("IN_KIND", "MEM")
    monkeypatch.setenv("IN_NAMESPACE", "namespace")
    monkeypatch.setenv("OUT_KIND", "MEM")
    monkeypatch.setenv("OUT_NAMESPACE", "namespace")
    import apihub.server

    class DummyDefinition(BaseModel):
        input_schema: Dict[str, Any]

    class Input(BaseModel):
        text: str
        probability: float

    def _get_definition_manager():
        class DummyDefinitionManager:
            def get(self, application):
                return DummyDefinition(input_schema=Input.schema())

        return DummyDefinitionManager()

    monkeypatch.setattr(
        apihub.server, "get_definition_manager", _get_definition_manager
    )

    response = client.post(
        "/async/test", params={"text": "this is simple"}, json={"probability": 0.6}
    )

    assert response.status_code == 200

    assert (
        len(
            apihub.server.get_state()
            .pipeline.destination_of(make_topic("test"))
            .results
        )
        == 1
    )

    assert (
        apihub.server.get_state().pipeline.destination_of(make_topic("test")).topic
        == "test"
    )


def test_sync_service_json(client, monkeypatch):
    monkeypatch.setenv("IN_KIND", "MEM")
    monkeypatch.setenv("IN_NAMESPACE", "namespace")
    monkeypatch.setenv("OUT_KIND", "MEM")
    monkeypatch.setenv("OUT_NAMESPACE", "namespace")
    import apihub.server

    class DummyDefinition(BaseModel):
        input_schema: Dict[str, Any]

    class Input(BaseModel):
        text: str
        probability: float

    def _get_definition_manager():
        class DummyDefinitionManager:
            def get(self, application):
                return DummyDefinition(input_schema=Input.schema())

        return DummyDefinitionManager()

    _get_redis = mock.MagicMock()
    _get_redis.return_value.get.return_value = apihub.server.Result(
        user="sync",
        api="test",
        status=apihub.server.Status.PROCESSED,
    ).json()

    monkeypatch.setattr(
        apihub.server, "get_definition_manager", _get_definition_manager
    )
    monkeypatch.setattr(apihub.server, "get_redis", _get_redis)

    response = client.post(
        "/sync/test", params={"text": "this is simple"}, json={"probability": 0.6}
    )

    assert _get_redis.called

    assert response.status_code == 200

    assert (
        apihub.server.get_state().pipeline.destination_of(make_topic("test")).topic
        == "test"
    )

    assert response.json()["result"]["user"] == "sync"
    assert response.json()["result"]["result"] == {}


def test_define_service(client):
    response = client.get(
        "/define/test",
    )
    assert response.status_code == 200


def test_redoc(client, monkeypatch):
    monkeypatch.setenv("IN_KIND", "MEM")
    monkeypatch.setenv("IN_NAMESPACE", "namespace")
    monkeypatch.setenv("OUT_KIND", "MEM")
    monkeypatch.setenv("OUT_NAMESPACE", "namespace")
    import apihub.server

    class DummyDefinition(BaseModel):
        input_schema: Dict[str, Any]

    class Input(BaseModel):
        text: str
        probability: float

    def _get_definition_manager():
        class DummyDefinitionManager:
            def get(self, application):
                return DummyDefinition(input_schema=Input.schema())

        return DummyDefinitionManager()

    monkeypatch.setattr(
        apihub.server, "get_definition_manager", _get_definition_manager
    )

    response = client.get("/redoc")
    assert response.status_code == 200
