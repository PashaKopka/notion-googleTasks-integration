import datetime
import json

import requests
from notion import notion_utils
from notion.notion_utils import notion_request_decorator
from notion.notion_props import AbstractNotionProperty, NotionPropertyFabric
from config import NOTION_TOKEN, NOTION_DATABASE_ID


class NotionDatabase:
    NOTION_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
    DATABASE_URL_FORMAT = 'https://api.notion.com/v1/databases/{}/query'
    CREATE_PAGE_URL = 'https://api.notion.com/v1/pages'
    PAGE_URL_FORMAT = 'https://api.notion.com/v1/pages/{}'
    SYNC_LIST_ROW_NAME = 'sync_list_id'

    def __init__(
        self,
        title_prop_name: str,
        database_id: str = NOTION_DATABASE_ID,
        token: str = NOTION_TOKEN,
    ) -> None:
        """
        database id is a simple ID of notion database
        token is a secret token from notion integration
        title_prop_name is a name of row in notion database that contains title of task
        content of this property will be used to save tasks to other lists as title
        """
        self._database_id = database_id
        self._token = token
        self._headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-02-22'
        }
        self._database_url = self.DATABASE_URL_FORMAT.format(database_id)

        self.title_prop_name = title_prop_name

    def get_prop_value(self, row: dict, prop_name: str):
        return row['props'][prop_name].value

    def get_synced_rows_ids(self) -> list[str]:
        return [
            self.get_prop_value(row, self.SYNC_LIST_ROW_NAME)
            for row in self._get_database_rows().values()
        ]

    @notion_request_decorator
    def _make_notion_request(self, url: str, method: str = 'POST', data: dict = None) -> requests.Response:
        data = json.dumps(data) if data else None
        return requests.request(
            method,
            url,
            headers=self._headers,
            data=data
        )

    def _get_database_rows(self) -> dict:
        res = self._make_notion_request(url=self._database_url)
        data = res.json()['results']
        rows = {}

        for row in data:
            rows[row['id']] = self._parse_row(row)

        return rows

    def _parse_row(self, row: dict) -> dict:
        row_data = {
            'id': row['id'],
            'object_type': row['object'],
            'created_time': datetime.datetime.strptime(row['created_time'], self.NOTION_DATE_FORMAT),
            'updated_time': datetime.datetime.strptime(row['last_edited_time'], self.NOTION_DATE_FORMAT),
        }
        properties = {}
        for prop_name, prop_data in row['properties'].items():
            properties[prop_name] = self.create_property(
                prop_name, prop_data)

        row_data['props'] = properties
        return row_data

    def _get_row_by_id(self, row_id: str) -> dict:
        res = self._make_notion_request(
            url=self.PAGE_URL_FORMAT.format(row_id), method='GET')
        row = res.json()
        return self._parse_row(row)

    def create_property(self, prop_name: str, prop_data: dict[str, str]) -> NotionPropertyFabric:
        return NotionPropertyFabric.create_notion_prop(
            prop_name, prop_data
        )

    def __getitem__(self, row_id: str) -> dict:
        return self._get_row_by_id(row_id)

    def get_all_rows(self) -> dict:
        return self._get_database_rows()

    def _update_row(self, row_id: str, *args: list[AbstractNotionProperty]) -> str:
        properties = {}
        for prop in args:
            data = prop.deserialize()
            properties.update(data)

        new_page_data = {
            'object': 'page',
            'parent': {
                'type': 'database_id',
                'database_id': self._database_id
            },
            'properties': properties
        }

        res = self._make_notion_request(
            method='PATCH',
            url=self.PAGE_URL_FORMAT.format(row_id),
            data=new_page_data
        )
        return res.json()['id']

    def update_row(self, notion_task_id, data):
        return self._update_row(notion_task_id, *data)

    def add_row_to_notion_database(self, sync_id: str, *args) -> str:
        properties = {}
        for prop in args:
            data = prop.deserialize()
            properties.update(data)
        
        if self.SYNC_LIST_ROW_NAME not in properties:
            properties[self.SYNC_LIST_ROW_NAME] = {
                'type': 'rich_text',
                'rich_text': [{
                    'type': 'text',
                    'text': {
                        'content': sync_id,
                    },
                }],
            }

        new_page_data = {
            'object': 'page',
            'parent': {
                'type': 'database_id',
                'database_id': self._database_id
            },
            'properties': properties
        }
        res = self._make_notion_request(
            url=self.CREATE_PAGE_URL,
            data=new_page_data
        )
        return res.json()['id']

    def get_not_synced_rows(self) -> dict:
        rows = self.get_all_rows()
        return {
            row_id: row for row_id, row in rows.items()
            if not row['props'][self.SYNC_LIST_ROW_NAME].value
        }


if __name__ == '__main__':
    db = NotionDatabase(
        'sync_list_id',
        NOTION_DATABASE_ID,
        NOTION_TOKEN
    )
    data = db.get_all_rows()
    print(data)
