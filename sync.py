import datetime
import time
import config
from google_tasks.google_utils import GoogleTaskStatus

from notion.notion_db import NotionDatabase
from google_tasks.google_tasks import GoogleTaskList
from notion.notion_props import AbstractNotionProperty, NotionText
from notion import notion_props


class NotionTasksSynchronizer:

    def __init__(self, notion: NotionDatabase, google_task_list: GoogleTaskList) -> None:
        self._notion_db = notion
        self._google_task_list = google_task_list

    def sync(self):
        not_synced_notion_items = self._notion_db.get_not_synced_rows()
        for item_id, item in not_synced_notion_items.items():
            self._add_notion_item_to_google_tasks(item_id, item)

        not_synced_google_items = self._google_task_list.get_not_synced_tasks()
        for item_id, item in not_synced_google_items.items():
            self._add_google_task_to_notion(item_id, item)

    def _add_google_task_to_notion(self, item_id: str, item: dict):
        data = [
            notion_props.NotionTitle('Name', item['title']),
            notion_props.NotionCheckbox('Checkbox', bool(item['status']))
        ]
        notion_task_id = self._notion_db.add_row_to_notion_database(
            item_id, *data
        )
        item['notes'] = notion_task_id
        item['updated'] = datetime.datetime.utcnow().strftime(
            self._google_task_list.GOOGLE_TIME_FORMAT
        )
        item['status'] = str(item['status'])
        self._google_task_list.update_task(item_id, item)

    def _add_notion_item_to_google_tasks(self, item_id: str, item: dict):
        props = item['props']
        google_task_id = self._google_task_list.add_task({
            'title': props[config.NOTION_TITLE_PROP_NAME].value,
            'notes': item_id,
            'due': None,
            'status': str(GoogleTaskStatus(props['Checkbox'].value)),
            'deleted': False,
        })
        google_task_id_prop = NotionText(  # TODO change NotionText init
            self._notion_db.SYNC_LIST_ROW_NAME, {
                'rich_text': [{
                    'plain_text': google_task_id
                }]
            }
        )
        self._notion_db.update_row(
            item_id, [google_task_id_prop]
        )


if __name__ == '__main__':
    notion = NotionDatabase(
        config.NOTION_DATABASE_ID,
        config.NOTION_TOKEN,
        config.NOTION_TITLE_PROP_NAME,
    )
    google_tasks = GoogleTaskList(
        config.GOOGLE_TASK_LIST_ID
    )
    syncer = NotionTasksSynchronizer(notion, google_tasks)

    while True:
        syncer.sync()
        time.sleep(10)
