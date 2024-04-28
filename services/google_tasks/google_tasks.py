import asyncio
import datetime
import os
import pickle

import aiohttp

import google_auth_oauthlib
import google_auth_oauthlib.flow

from config import GOOGLE_CLIENT_SECRET_FILE, GOOGLE_TASK_LIST_ID
from models.models import SyncedItem, get_db
from services.service import AbstractDataAdapter, AbstractService, Item


class GTasksDataAdapter(AbstractDataAdapter):

    def __init__(self, tasks_list_id) -> None:
        super().__init__()
        self._tasks_list_id = tasks_list_id

    def dict_to_item(self, data: dict) -> Item:
        return Item(
            name=data.get("title", ""),
            status=self.convert_status_to_bool(data.get("status")),
            google_task_id=data.get("id", ""),
            updated_at=self._get_updated_at(data.get("updated", "")),
        )

    def item_to_dict(self, item: Item) -> dict:
        return {
            "kind": "tasks#task",
            "id": item.google_task_id,
            "title": item.name,
            "status": self.convert_status_to_text(item.status),
        }

    def dicts_to_items(self, data: list[dict]) -> list[Item]:
        items = []
        for item_data in data:
            items.append(self.dict_to_item(item_data))

        return items

    def items_to_dicts(self, items: dict[Item]) -> list[dict]:
        dicts = []
        for item in items:
            dicts.append(self.item_to_dict(item))

        return dicts

    def convert_status_to_text(self, status: bool) -> str:
        return "completed" if status else "needsAction"

    def convert_status_to_bool(self, status: str) -> bool:
        return status == "completed"

    def _get_updated_at(self, updated: str) -> datetime:
        return datetime.datetime.fromisoformat(updated)


class GTasksList(AbstractService):
    GOOGLE_TASKS_SCOPES = ["https://www.googleapis.com/auth/tasks"]

    GOOGLE_TASKS_GET_ALL_URL = "https://www.googleapis.com/tasks/v1/lists/{}/tasks?showCompleted=true&showHidden=true"
    GOOGLE_TASKS_UPDATE_URL = "https://www.googleapis.com/tasks/v1/lists/{}/tasks/{}"
    GOOGLE_TASKS_ADD_URL = "https://www.googleapis.com/tasks/v1/lists/{}/tasks"

    def __init__(
        self,
        syncing_service_id: str,
        client_config: dict,
        tasks_list_id: str,
    ) -> None:
        super().__init__()
        self._client_config = client_config

        self._tasks_list_id = tasks_list_id
        self._data_adapter = GTasksDataAdapter(tasks_list_id)
        self._syncing_service_id = syncing_service_id

        self._pickle_file = "token_tasks_v1.pickle"

        self._session = aiohttp.ClientSession()
        self._credentials = None

        self._headers = {"Authorization": f"Bearer {self._client_config['token']}"}

    def refresh_token(func):
        async def wrapper(self, *args, **kwargs):
            try:
                return await func(self, *args, **kwargs)
            except aiohttp.ClientResponseError as e:
                if e.status == 401:
                    await self._refresh_token()
                    return await func(self, *args, **kwargs)
                else:
                    return await e.json()
        return wrapper

    async def _refresh_token(self):
        async with self._session.post(
            self._client_config["token_uri"],
            data={
                "client_id": self._client_config["client_id"],
                "client_secret": self._client_config["client_secret"],
                "refresh_token": self._client_config["refresh_token"],
                "grant_type": "refresh_token",
            },
        ) as response:
            data = await response.json()
            self._client_config["token"] = data["access_token"]
            self._client_config["expiry"] = data["expires_in"]
            self._headers["Authorization"] = f"Bearer {data['access_token']}"

    @refresh_token
    async def get_all_items(self) -> list[Item]:
        async with self._session.get(
            self._get_all_tasks_url, headers=self._headers
        ) as response:
            tasks_data = await response.json()
            return self._data_adapter.dicts_to_items(tasks_data.get("items", []))

    @refresh_token
    async def get_item_by_id(self, item_id: str) -> Item:
        url = self._update_task_url.format(item_id)
        async with self._session.get(url, headers=self._headers) as response:
            task_data = await response.json()
            return self._data_adapter.dict_to_item(task_data)

    @refresh_token
    async def update_item(self, item: Item) -> str:
        async with self._session.put(
            self._update_task_url.format(item.google_task_id),
            headers=self._headers,
            json=self._data_adapter.item_to_dict(item),
        ) as response:
            if response.status == 200:
                return f"Task {item.google_task_id} updated successfully."
            else:
                return await response.json()

    @refresh_token
    async def add_item(self, item: Item) -> str:
        async with self._session.post(
            self._add_task_url,
            headers=self._headers,
            json=self._data_adapter.item_to_dict(item),
        ) as response:
            data = await response.json()
            item.google_task_id = data.get("id")
            self._save_sync_ids(item)

    def _save_sync_ids(self, item: Item) -> None:
        synced_item = SyncedItem.create_from_item(item, self._syncing_service_id)
        synced_item.save()

    @property
    def _get_all_tasks_url(self) -> str:
        return self.GOOGLE_TASKS_GET_ALL_URL.format(self._tasks_list_id)

    @property
    def _update_task_url(self) -> str:
        return self.GOOGLE_TASKS_UPDATE_URL.format(self._tasks_list_id, "{}")

    @property
    def _add_task_url(self) -> str:
        return self.GOOGLE_TASKS_ADD_URL.format(self._tasks_list_id)


async def main():
    google_tasks = GTasksList(
        syncing_service_id="234",
        client_config=GOOGLE_CLIENT_SECRET_FILE,
        tasks_list_id=GOOGLE_TASK_LIST_ID,
    )

    tasks = await google_tasks.get_all_items()
    print(tasks)
    t = tasks[0]
    t.name = "New name"
    res = await google_tasks.update_item(t)
    print(res)

    res = await google_tasks.add_item(
        Item(name="My new task", status=False, notion_id="some_id", google_task_id="")
    )
    print(res)

    new_t = await google_tasks.get_item_by_id(t.google_task_id)
    print(new_t)


if __name__ == "__main__":
    asyncio.run(main())
