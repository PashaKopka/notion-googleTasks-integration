import requests

from config import NOTION_VERSION
from services.service import AbstractProfiler


class NotionProfiler(AbstractProfiler):
    SEARCH_URL = "https://api.notion.com/v1/search"

    def __init__(
        self,
        token: str,
    ) -> None:
        self._token = token
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        }
        self._session = requests.Session()

    def get_lists(self) -> list[dict]:
        response = self._session.post(
            self.SEARCH_URL,
            headers=self._headers,
            json={
                "query": "External tasks",
                "filter": {
                    "property": "object",
                    "value": "database",
                },
                "sort": {
                    "direction": "ascending",
                    "timestamp": "last_edited_time",
                },
            },
        )
        data = response.json()
        return self._database_result(data.get("results", []))

    def _database_result(self, results: list[dict]) -> dict:
        return {
            data["id"]: {
                "title": data["title"][0]["plain_text"],
                "id": data["id"],
            }
            for data in results
        }
