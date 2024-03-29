from unittest.mock import patch

import pytest

from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import Dict, Any
from openapi_spec_validator import validate_spec, openapi_v30_spec_validator

from apihub.common.db_session import create_session
from apihub.subscription.depends import require_subscription, SubscriptionToken
from apihub.subscription.schemas import SubscriptionTier
from apihub.utils import make_topic


@pytest.fixture(scope="function")
def client(monkeypatch):
    def _create_session():
        pass

    def _ip_rate_limited():
        pass


    monkeypatch.setenv("OUT_KIND", "MEM")

    from apihub.server import api, ip_rate_limited

    api.dependency_overrides[ip_rate_limited] = _ip_rate_limited
    api.dependency_overrides[create_session] = _create_session

    yield TestClient(api)


def test_slash(client):
    status_codes = []
    for i in range(20):
        response = client.get("/")
        status_codes.append(response.status_code)
    assert len(status_codes) == 20
    # assert len(list(filter(lambda x: x == 200, status_codes))) == 10


def test_async_service_json(client, db_session, monkeypatch):
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
    token = SubscriptionToken(
        user_id=1, subscription_id=1, application_id=1,
        email="user@test.com", tier=SubscriptionTier.TRIAL, application="test",
        role="user", name="user", expires_days=1,
    )

    response = client.post(
        "/async/test", params={"text": "this is simple"}, json={"probability": 0.6},
        headers={"Authorization": f"Bearer {token.access_token}"}
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


def test_define_service(client):
    response = client.get(
        "/define/test",
    )
    assert response.status_code == 200


def test_async_service_json_validation_error(client, db_session, monkeypatch):
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

    token = SubscriptionToken(
        user_id=1, subscription_id=1, application_id=1,
        email="user@test.com", tier=SubscriptionTier.TRIAL, application="test",
        role="user", name="user", expires_days=1,
    )

    response = client.post(
        "/async/test", params={}, json={"probability": 0.6},
        headers={"Authorization": f"Bearer {token.access_token}"}
    )

    assert response.status_code == 422


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

def test_openapi(client, monkeypatch):
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

    schema = apihub.server.custom_openapi()
    validate_spec(schema, validator=openapi_v30_spec_validator)
