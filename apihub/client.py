import json
from typing import Optional, Any, Dict

import requests
from pydantic import BaseSettings

from apihub_users.security.router import UserCreate
from apihub_users.subscription.router import SubscriptionIn


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
                "settings": self.settings.dict(),
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
            print(response.json())
            self.token = response.json()["access_token"]
        else:
            print(response.json())

    def create_user(self, user):
        username = user["username"]
        response = requests.post(
            self._make_url(f"user/{username}"),
            headers={"Authorization": f"Bearer {self.token}"},
            json=UserCreate.parse_obj(user).dict(),
        )
        print(response.json())
        if response.status_code == 200:
            print(response.json())

    def create_subscription(self, subscription):
        response = requests.post(
            self._make_url("subscription"),
            headers={"Authorization": f"Bearer {self.token}"},
            json=SubscriptionIn.parse_obj(subscription).dict(),
        )
        if response.status_code == 200:
            return True
        else:
            raise Exception(response.json())

    def refresh_application_token(self, application: str) -> None:
        # TODO exceptions
        response = requests.get(
            self._make_url(f"token/{application}"),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if response.status_code == 200:
            print(response.json())
            self.applications[application] = response.json()["token"]
        else:
            print(response.text)
            print(response.json())

    def _check_token_for(self, application: str) -> bool:
        return application in self.applications

    def async_request(self, application: str, data: dict):
        response = requests.post(
            self._make_url(f"async/{application}"),
            headers={
                "Authorization": f"Bearer {self.applications[application]}",
            },
            json=data,
        )
        if response.status_code == 200:
            return response.json()
        else:
            return response.json()

    def async_result(self, application: str, key: str):
        # TODO wait and timeout
        response = requests.get(
            self._make_url(f"async/{application}"),
            params={
                "key": key,
            },
            headers={
                "Authorization": f"Bearer {self.token}",
            },
        )
        if response.status_code == 200:
            return response.json()
        else:
            return response.json()
