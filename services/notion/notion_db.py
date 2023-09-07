import asyncio
import datetime
import json
import httpx

import requests
from data_row import DataRow
from services.notion.notion_utils import notion_request_decorator, notion_async_request_decorator
from services.notion.notion_props import AbstractNotionProperty, NotionPropertyFabric
from services.service import AbstractService, AbstractDataRowAdapter
from config import NOTION_TITLE_PROP_NAME, NOTION_DATABASE_ID, NOTION_TOKEN


class NotionDataRowAdapter(AbstractDataRowAdapter):
    
    def __init__(self, database_id: str, date_format: str) -> None:
        self._date_format = date_format
        self._database_id = database_id
    
    def dict_to_data_row(self, row: dict) -> DataRow:
        data_row = DataRow(
            id=row['id'],
            object_type=row['object'],
            created_time=datetime.datetime.strptime(row['created_time'], self._date_format),
            updated_time=datetime.datetime.strptime(row['last_edited_time'], self._date_format),
        )
        for prop_name, prop_data in row['properties'].items():
            prop = self._create_property(prop_name, prop_data)
            data_row.add_prop(prop_name, prop)

        return data_row
    
    def data_row_to_dict(self, data_row: DataRow) -> dict:
        return {
            "object": "page",
            "parent": {
                "type": "database_id",
                "database_id": self._database_id
            },
            "properties": data_row.props_as_dict()
        }

    def _create_property(self, prop_name: str, prop_data: dict[str, str]) -> AbstractNotionProperty:
        return NotionPropertyFabric.create_notion_prop(
            prop_name, prop_data
        )
    
    def dicts_to_data_rows(self, notion_data: dict) -> list[DataRow]:
        return [self.dict_to_data_row(row) for row in notion_data]

    def data_rows_to_dicts(self, data_rows: list[DataRow]) -> list[dict]:
        return [
            self.data_row_to_dict(row)
            for row in data_rows
        ]


class NotionDatabaseService(AbstractService):
    NOTION_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
    DATABASE_URL_FORMAT = 'https://api.notion.com/v1/databases/{}/query'
    CREATE_PAGE_URL = 'https://api.notion.com/v1/pages'
    PAGE_URL_FORMAT = 'https://api.notion.com/v1/pages/{}'
    SYNC_LIST_ROW_NAME = 'sync_list_id'
    
    def __init__(
        self,
        database_id: str,
        token: str,
        title_prop_name: str = NOTION_TITLE_PROP_NAME,
    ) -> None:
        """
        database id is a simple ID of notion database
        token is a secret token from notion integration
        title_prop_name is a name of row in notion database that contains title of task
        content of this property will be used to save tasks to other lists as title
        """
        super().__init__()
        
        self._database_id = database_id
        self._token = token
        self._headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-02-22'
        }
        self._database_url = self.DATABASE_URL_FORMAT.format(database_id)

        self.title_prop_name = title_prop_name

        self._data_adapter = NotionDataRowAdapter(self._database_id, self.NOTION_DATE_FORMAT)
    
    @notion_request_decorator
    def _make_request(self, url: str, method: str = 'POST', data: dict = None) -> requests.Response:
        data = json.dumps(data) if data else None
        return requests.request(
            method,
            url,
            headers=self._headers,
            data=data
        )
    
    @notion_async_request_decorator
    async def _make_request_async(
        self,
        url: str,
        method: str = 'POST',
        data: dict = None
    ) -> list[httpx.Response]:
        data = json.dumps(data) if data else None
        async with httpx.AsyncClient() as client:
            res = await client.request(
                method,
                url,
                headers=self._headers,
                data=data
            )
            return res
    
    def get_data(self) -> list[DataRow]:
        notion_data = self._get_data()
        return self._data_adapter.dicts_to_data_rows(notion_data)
    
    def get_new_data(self) -> list[DataRow]:
        data = self._get_new_data()
        return self._data_adapter.dicts_to_data_rows(data)
    
    def update_data(self, data: list[DataRow]) -> bool:
        # we can know if data already exists in notion database
        # by checking if it has notion_id in DataRow.sync_id
        # if it has, we can update it, if not, we can add it
        
        new_data, synced_data = DataRow.filter_not_synced_rows(data)
        add_res = self._add_new_data(new_data)
        
        update_res = self._update_data(synced_data)
        
        return all([add_res, update_res])
    
    def _get_data_by_id(self, data_id: str) -> dict:
        res = self._make_request(
            url=self.PAGE_URL_FORMAT.format(data_id), method='GET'
        )
        row = res.json()
        return self._data_adapter.data_row_from_notion_row(row)
    
    def _get_data(self) -> list[dict]:
        res = self._make_request(url=self._database_url)
        data = res.json()['results']
        return self._data_adapter.dicts_to_data_rows(data)

    def _get_new_data(self) -> list[dict]:
        rows = self.get_all_rows()
        return {
            row_id: row for row_id, row in rows.items()
            if not row['props'][self.SYNC_LIST_ROW_NAME].value
        }
    
    def _update_data(self, data: list[DataRow]) -> bool:
        # we can send async requests to create many pages at once
        loop = asyncio.get_event_loop()
        tasks = [self._update_row_async(row) for row in data]
        results = loop.run_until_complete(asyncio.gather(*tasks))
        
        return all(results)
    
    def _add_new_data(self, data: list[DataRow]) -> bool:
        # we can send async requests to create many pages at once
        loop = asyncio.get_event_loop()
        tasks = [self._add_row_async(row) for row in data]
        results = loop.run_until_complete(asyncio.gather(*tasks))
        
        return all(results)

    async def _add_row_async(self, data: DataRow) -> bool:
        res = await self._make_request_async(
            self.CREATE_PAGE_URL,
            method='POST',
            data=self._data_adapter.data_row_to_dict(data)
        )
        data.sync_id = res.json()['id']
        # if res.status_code != 200: _make_request_async will raise exception
        return True

    async def _update_row_async(self, data: DataRow) -> bool:
        res = await self._make_request_async(
            self.PAGE_URL_FORMAT.format(data.sync_id),
            method='PATCH',
            data=self._data_adapter.data_row_to_dict(data)
        )
        data.sync_id = res.json()['id']
        # if res.status_code != 200: _make_request_async will raise exception
        return True
    
    def __getitem__(self, notion_id: str) -> DataRow:
        data = self._get_data_by_id(notion_id)
        return self._data_adapter.data_row_from_notion_row(data)


if __name__ == '__main__':
    db = NotionDatabaseService(
        NOTION_DATABASE_ID,
        NOTION_TOKEN,
        'sync_list_id',
    )
    dr1 = DataRow()
    dr1.add_prop('title', NotionPropertyFabric.create_notion_prop('Name', {'type': 'title', 'title': [{'plain_text': 'test'}]}))
    dr2 = DataRow()
    dr2.add_prop('title', NotionPropertyFabric.create_notion_prop('Name', {'type': 'title', 'title': [{'plain_text': 'test2'}]}))
    dr3 = DataRow()
    dr3.add_prop('title', NotionPropertyFabric.create_notion_prop('Name', {'type': 'title', 'title': [{'plain_text': 'test3'}]}))
    dr4 = DataRow()
    dr4.add_prop('title', NotionPropertyFabric.create_notion_prop('Name', {'type': 'title', 'title': [{'plain_text': 'test4'}]}))
    dr5 = DataRow()
    dr5.add_prop('title', NotionPropertyFabric.create_notion_prop('Name', {'type': 'title', 'title': [{'plain_text': 'test5'}]}))
    dr6 = DataRow()
    dr6.add_prop('title', NotionPropertyFabric.create_notion_prop('Name', {'type': 'title', 'title': [{'plain_text': 'test6'}]}))
    
    db.update_data(
        [dr1, dr2]
    )
    print(dr2.sync_id)
    dr2._props['title']._value = 'test2 updated'
    db.update_data([dr2])