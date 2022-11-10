from unittest.mock import patch

import pytest

from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import Dict, Any


from apihub.activity.models import Activity
from apihub.activity.queries import ActivityQuery
from apihub.common.db_session import create_session
from apihub.subscription.depends import require_subscription
from apihub.subscription.schemas import SubscriptionTier, SubscriptionBase


@pytest.fixture(scope="function")
def client(monkeypatch):
    def _create_session():
        pass

    def _ip_rate_limited():
        pass

    def _require_subscription():
        return SubscriptionBase(
            username="test", tier=SubscriptionTier.TRIAL, application="app1"
        )

    monkeypatch.setenv("OUT_KIND", "MEM")

    from apihub.server import api, ip_rate_limited

    api.dependency_overrides[ip_rate_limited] = _ip_rate_limited
    api.dependency_overrides[require_subscription] = _require_subscription

    api.dependency_overrides[create_session] = _create_session

    yield TestClient(api)


def test_slash(client):
    status_codes = []
    for i in range(20):
        response = client.get("/")
        status_codes.append(response.status_code)
    assert len(status_codes) == 20
    # assert len(list(filter(lambda x: x == 200, status_codes))) == 10


def test_async_service(client, db_session):
    application = "app1"
    r = f"/async/{application}"
    response = client.post(r)
    assert response.status_code == 200
    query = ActivityQuery(db_session)
    assert query.get_query().filter(Activity.request == r).one().request == r
    with patch("apihub.activity.models.Activity.create_activity_helper") as mock_obj:
        application = "app2"
        response = client.post(
            f"/async/{application}",
            params={"text": "this is simple"},
        )
        assert response.status_code == 200
        mock_obj.assert_called()


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
