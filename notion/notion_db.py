import datetime

import requests
from notion import notion_utils
from notion.notion_utils import notion_request_decorator
from notion.notion_props import NotionPropertyFabric
from config import NOTION_TOKEN, NOTION_DATABASE_ID


class NotionDatabase:
    NOTION_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
    DATABASE_URL_FORMAT = 'https://api.notion.com/v1/databases/{}/query'
    NOTION_PARSERS = {  # TODO delete this
        'checkbox': notion_utils.parse_checkbox,
        'title': notion_utils.parse_title,
        'last_edited_time': notion_utils.parse_last_edited_time,
    }

    def __init__(self, database_id: str, token: str, title_prop_name: str) -> None:
        self._database_id = database_id  # TODO maybe should remove this
        self._token = token  # TODO maybe should remove this
        self._headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-02-22'
        }
        self._database_url = self.DATABASE_URL_FORMAT.format(database_id)
        self.title_prop_name = title_prop_name
    
    @notion_request_decorator
    def _make_get_data_request(self):
        return requests.request(
            'POST',
            self._database_url,
            headers=self._headers
        )

    def _get_database_rows(self, exclude_rows_ids: list | tuple = ()) -> dict:
        res = self._make_get_data_request()
        data = res.json()['results']
        rows = {}
        for row in data:
            if row['id'] in exclude_rows_ids:
                continue

            row_data = {
                'id': row['id'],  # TODO maybe not needed
                'object_type': row['object'],
                'created_time': datetime.datetime.strptime(row['created_time'], self.NOTION_DATE_FORMAT),
                'updated_time': datetime.datetime.strptime(row['last_edited_time'], self.NOTION_DATE_FORMAT),
            }
            properties = {}  # TODO maybe better to use dict
            for prop_name, prop_data in row['properties'].items():
                properties[prop_name] = NotionPropertyFabric.create_notion_prop(prop_name, prop_data)

            row_data['props'] = properties
            rows[row['id']] = row_data

        return rows

    def __getitem__(self, key):
        return self._get_database_rows()[key]

    def get_all_rows(self) -> dict:
        return self._get_database_rows()

    def get_new_rows(self, exclude_ids) -> dict:
        return self._get_database_rows(exclude_ids)


if __name__ == '__main__':
    db = NotionDatabase(
        NOTION_DATABASE_ID,
        NOTION_TOKEN
    )
    data = db.get_all_rows()
    print(data)
