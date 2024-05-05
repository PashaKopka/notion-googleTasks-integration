from functools import wraps

import requests

from services.service import AbstractProfiler


class GTasksProfiler(AbstractProfiler):
    GET_TASK_LISTS_URL = "https://tasks.googleapis.com/tasks/v1/users/@me/lists/"

    def __init__(
        self,
        client_config: str,
    ) -> None:
        self._client_config = client_config

        self._session = requests.Session()

        self._headers = {"Authorization": f"Bearer {self._client_config['token']}"}

    def refresh_token(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except requests.HTTPError as e:
                if e.response.status_code == 401:
                    self._refresh_token()
                    return func(self, *args, **kwargs)
                else:
                    return e.json()

        return wrapper

    def _refresh_token(self) -> None:
        response = self._session.post(
            self._client_config["token_uri"],
            data={
                "client_id": self._client_config["client_id"],
                "client_secret": self._client_config["client_secret"],
                "refresh_token": self._client_config["refresh_token"],
                "grant_type": "refresh_token",
            },
        )
        data = response.json()
        self._client_config["token"] = data["access_token"]
        self._client_config["expiry"] = data["expires_in"]
        self._headers["Authorization"] = f"Bearer {data['access_token']}"

    @refresh_token
    def get_lists(self) -> list[dict]:
        response = self._session.get(
            self.GET_TASK_LISTS_URL,
            headers=self._headers,
        )
        response.raise_for_status()
        tasks_data = response.json()
        return self._database_result(tasks_data.get("items", []))

    def _database_result(self, results: list[dict]) -> dict:
        return {
            data["id"]: {
                "title": data["title"],
                "id": data["id"],
            }
            for data in results
        }
