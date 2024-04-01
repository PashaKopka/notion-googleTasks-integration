import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
import aiohttp
import asyncio
from config import GOOGLE_CLIENT_SECRET_FILE, GOOGLE_TASK_LIST_ID
from services.service import AbstractService, Item, AbstractDataAdapter


class GTasksDataAdapter(AbstractDataAdapter):
    GOOGLE_TASK_URL = 'https://www.googleapis.com/tasks/v1/lists/{}/tasks/{}'
    
    def __init__(self, tasks_list_id) -> None:
        super().__init__()
        self._tasks_list_id = tasks_list_id

    def dict_to_item(self, data: dict) -> Item:
        return Item(
            name=data.get('title', ''),
            status=self.convert_status_to_bool(data.get('status')),
            service_1_id='',
            service_2_id=data.get('id', '')
        )

    def item_to_dict(self, item: Item) -> dict:
        return {
            "kind": "tasks#task",
            "id": item.service_2_id,
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
        return 'completed' if status else 'needsAction'
    
    def convert_status_to_bool(self, status: str) -> bool:
        return status == 'completed'

    @property
    def _task_url(self) -> str:
        return self.GOOGLE_TASK_URL.format(self._tasks_list_id, '{}')


class GTasksList(AbstractService):
    GOOGLE_TASKS_SCOPES = [
        'https://www.googleapis.com/auth/tasks']

    GOOGLE_TASKS_GET_ALL_URL = 'https://www.googleapis.com/tasks/v1/lists/{}/tasks'
    GOOGLE_TASKS_UPDATE_URL = 'https://www.googleapis.com/tasks/v1/lists/{}/tasks/{}'
    GOOGLE_TASKS_ADD_URL = 'https://www.googleapis.com/tasks/v1/lists/{}/tasks'

    def __init__(
        self,
        credentials_file_path: str,
        tasks_list_id: str,
    ) -> None:
        super().__init__()
        self._credentials_file_path = credentials_file_path
        self._tasks_list_id = tasks_list_id
        self._data_adapter = GTasksDataAdapter(tasks_list_id)
        
        self._pickle_file = 'token_tasks_v1.pickle'
        
        self._session = aiohttp.ClientSession()
        self._credentials = None
        
        self._create_google_connect()
        self._headers = {'Authorization': f'Bearer {self._credentials.token}'}
        
    def _create_google_connect(self) -> None:
        if os.path.exists(self._pickle_file):
            with open(self._pickle_file, 'rb') as token:
                self._credentials = pickle.load(token)

        if not self._credentials or not self._credentials.valid:
            self._flow = InstalledAppFlow.from_client_secrets_file(
                self._credentials_file_path,
                self.GOOGLE_TASKS_SCOPES
            )
            self._credentials = self._flow.run_local_server(port=0)
            with open(self._pickle_file, 'wb') as token:
                pickle.dump(self._credentials, token)
        
    async def get_all_items(self) -> list[Item]:
        async with self._session.get(self._get_all_tasks_url, headers=self._headers) as response:
            tasks_data = await response.json()
            return self._data_adapter.dicts_to_items(tasks_data.get('items', []))

    async def get_item_by_id(self, item_id: str) -> Item:
        url = self._update_task_url.format(item_id)
        async with self._session.get(url, headers=self._headers) as response:
            task_data = await response.json()
            return self._data_adapter.dict_to_item(task_data)

    async def update_item(self, item_id: str, data: Item) -> str:
        async with self._session.put(
            self._update_task_url.format(item_id),
            headers=self._headers,
            json=self._data_adapter.item_to_dict(data)
        ) as response:
            if response.status == 200:
                return f"Task {item_id} updated successfully."
            else:
                return await response.json()

    async def add_item(self, data: Item) -> str:
        async with self._session.post(
            self._add_task_url,
            headers=self._headers,
            json=self._data_adapter.item_to_dict(data)
        ) as response:
            if response.status == 200:
                return "Task added successfully."
            else:
                return "Error adding task."

    @property
    def _get_all_tasks_url(self) -> str:
        return self.GOOGLE_TASKS_GET_ALL_URL.format(self._tasks_list_id)

    @property
    def _update_task_url(self) -> str:
        return self.GOOGLE_TASKS_UPDATE_URL.format(self._tasks_list_id, '{}')

    @property
    def _add_task_url(self) -> str:
        return self.GOOGLE_TASKS_ADD_URL.format(self._tasks_list_id)

async def main():
    google_tasks = GTasksList(
        GOOGLE_CLIENT_SECRET_FILE,
        GOOGLE_TASK_LIST_ID
    )

    tasks = await google_tasks.get_all_items()
    print(tasks)
    t = tasks[0]
    t.name = 'New name'
    res = await google_tasks.update_item(t.service_2_id, t)
    print(res)

    res = await google_tasks.add_item(Item(name='My new task', status=False, service_1_id='some_id', service_2_id=''))
    print(res)

    new_t = await google_tasks.get_item_by_id(t.service_2_id)
    print(new_t)

if __name__ == "__main__":
    asyncio.run(main())
