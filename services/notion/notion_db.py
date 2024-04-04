import asyncio
import uuid
import aiohttp
from config import NOTION_DATABASE_ID, NOTION_TITLE_PROP_NAME, NOTION_TOKEN
from models.models import SyncedItem
from services.service import AbstractService, Item, AbstractDataAdapter


class NotionDBDataAdapter(AbstractDataAdapter):

    def __init__(
        self,
        title_prop_name: str,
        database_id: str,
    ) -> None:
        super().__init__()
        self._title_prop_name = title_prop_name
        self._database_id = database_id

    def dict_to_item(self, data: dict) -> Item:
        return Item(
            name=self._get_title(data),
            status=self._get_checkbox_status(data),
            service_1_id=data.get('id', ''),
            service_2_id=self._get_sync_id(data.get('id', ''))
        )

    def item_to_dict(self, item: Item) -> dict:
        return {
            "object": "page",
            "id": item.service_1_id or str(uuid.uuid4()),
            "parent": {
                "type": "database_id",
                "database_id": self._database_id
            },
            "properties": {
                "Checkbox": {
                    "checkbox": item.status
                },
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": item.name,
                            },
                            "plain_text": item.name,
                        }
                    ]
                }
            },
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

    def _get_title(self, data: dict) -> str:
        title_field = data.get('properties', {}).get(self._title_prop_name, {}).get('title') or [{}]
        return title_field[0].get('plain_text', '')

    def _get_checkbox_status(self, data: dict) -> bool:
        return data.get(
            'properties', {}
        ).get('Checkbox', {}).get(
            'checkbox', False
        )

    def _get_sync_id(self, item_id: str) -> str:
        item = SyncedItem.get_by_sync_id(service_1_id=item_id)
        if item:
            return item.service_2_id
        return ''


class NotionDB(AbstractService):
    DATABASE_URL_FORMAT = 'https://api.notion.com/v1/databases/{}/query'
    CREATE_PAGE_URL = 'https://api.notion.com/v1/pages'
    PAGE_URL_FORMAT = 'https://api.notion.com/v1/pages/{}'

    def __init__(
        self,
        syncing_service_id: str,
        database_id: str,
        token: str,
        title_prop_name: str
    ) -> None:
        super().__init__()

        self._database_id = database_id
        self._token = token
        self._headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-02-22'
        }
        self._database_url = self.DATABASE_URL_FORMAT.format(database_id)
        self._title_prop_name = title_prop_name
        self._session = aiohttp.ClientSession()

        self._data_adapter = NotionDBDataAdapter(title_prop_name, database_id)
        self._syncing_service_id = syncing_service_id

    async def get_all_items(self) -> list[Item]:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self._database_url,
                headers=self._headers
            ) as response:
                data = await response.json()
                return self._data_adapter.dicts_to_items(data.get('results'))

    async def get_item_by_id(self, item_id: str) -> Item:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                self.PAGE_URL_FORMAT.format(item_id),
                headers=self._headers
            ) as response:
                data = await response.json()
                return self._data_adapter.dict_to_item(data)

    async def update_item(self, item_id: str, data: Item) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                self.PAGE_URL_FORMAT.format(item_id),
                headers=self._headers,
                json=self._data_adapter.item_to_dict(data)
            ) as response:
                return await response.json()

    async def add_item(self, item: Item) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.CREATE_PAGE_URL,
                headers=self._headers,
                json=self._data_adapter.item_to_dict(item)
            ) as response:
                data = await response.json()
                item.service_1_id = data.get('id')
                self._save_sync_ids(item)

    def _save_sync_ids(self, item: Item) -> None:
        synced_item = SyncedItem(
            service_1_id=item.service_1_id,
            service_2_id=item.service_2_id,
            syncing_service_id=self._syncing_service_id
        )
        synced_item.save()


async def main():
    notion = NotionDB(
        NOTION_DATABASE_ID,
        NOTION_TOKEN,
        NOTION_TITLE_PROP_NAME
    )

    items = await notion.get_all_items()
    # print(items)
    i = items[0]
    i.name = 'New name'
    res = await notion.update_item(i.service_1_id, i)

    res = await notion.add_item(
        Item(
            name='My new task',
            status=False,
            service_1_id=str(uuid.uuid4()),
            service_2_id=''
        )
    )

    print(res)

if __name__ == "__main__":
    asyncio.run(main())
