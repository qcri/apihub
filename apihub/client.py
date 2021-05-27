import json
from typing import Optional, Any, Dict

import requests
from pydantic import BaseSettings


class ClientSettings(BaseSettings):
    endpoint: str = "http://localhost"
    token: Optional[str] = None


class Client:
    def __init__(self, settings: Dict[str, Any]) -> None:
        if settings is not None:
            self.settings = ClientSettings.parse_obj(settings)
        else:
            self.settings = ClientSettings()
        self.token: Optional[str] = None
        self.applications: Dict[str, Any] = {}

    def _make_url(self, path: str) -> str:
        return f"{self.settings.endpoint}/{path}"

    def save_state(self, filename="~/.apihubrc") -> None:
        json.dump(
            {
                "settings": self.settings,
                "token": self.token,
                "applications": self.applications,
            },
            open(filename, "w"),
        )

    @staticmethod
    def load_state(filename="~/.apihubrc") -> "Client":
        state = json.load(open(filename))
        client = Client(state["settings"])
        client.token = state["token"]
        client.applications = state["applications"]
        return client

    def authenticate(self, username: str, password: str) -> None:
        # TODO exceptions
        response = requests.get(
            self._make_url("_authenticate"),
            auth=(username, password),
        )
        if response.status_code == 200:
            self.token = response.json()["token"]

    def refresh_application_token(self, application: str) -> None:
        # TODO exceptions
        response = requests.get(
            self._make_url(f"token/{application}"),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if response.status_code == 200:
            self.applications[application] = response.json()["token"]

    def _check_token_for(self, application: str) -> bool:
        return application in self.applications

    def async_request(self, application: str, params: Dict[str, Any]):
        response = requests.post(
            self._make_url(f"async/{application}"),
            headers={
                "Authorization": f"Bearer {self.applications[application]}",
            },
        )
        if response.status_code == 200:
            return response.json()

    def async_result(self, application: str, key: str):
        # TODO wait and timeout
        response = requests.get(
            self._make_url(f"async/{application}"),
            headers={
                "Authorization": f"Bearer {self.applications[application]}",
            },
        )
        if response.status_code == 200:
            return response.json()
