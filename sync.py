import time
import config

from notion.notion_db import NotionDatabase
from google_tasks.google_tasks import GoogleTaskList
from notion.notion_props import AbstractNotionProperty


class NotionTasksSynchronizer:

    def __init__(self, notion: NotionDatabase, google_task_list: GoogleTaskList) -> None:
        self._notion = notion
        self._google_task_list = google_task_list
        self._synced_notion_items_ids = []  # notion items ids, which are already uploaded to google task list
    
    def update_google_task_list(self):
        """
        Firstly we should get all tasks inside google task list
        There will be notion items ids in notes field
        We can know, which notion items are already uploaded to google task list
        """
        notion_items_ids_in_google_tasks = self._google_task_list.get_notion_ids()
        self._synced_notion_items_ids.extend(notion_items_ids_in_google_tasks)
        new_notion_items = self._notion.get_new_rows(self._synced_notion_items_ids)
        
        for notion_item_id, notion_item in new_notion_items.items():
            self._upload_notion_item_to_google_item(notion_item_id, notion_item)
    
    def update_notion_database(self):
        """
        Here we should get tasks from google task list, 
        where notes field has not notion item id. These tasks 
        means new tasks which were created in google task list
        We should create new notion items for these tasks, get their ids
        and update notes field in google task list
        """
        new_google_tasks = self._google_task_list.get_new_google_tasks()
        for task_id, task_data in new_google_tasks.items():
            self._upload_google_task_to_notion_database(task_id, task_data)

    def sync(self):
        self.update_google_task_list()
        self.update_notion_database()
    
    def _upload_google_task_to_notion_database(self, task_id: str, task_data: dict) -> None:
        new_page_id = self._notion.add_row_to_notion_database(
            task_data['title'],
            bool(task_data['status'])
        )
        task_data['notes'] = new_page_id
        self._update_google_task(task_id=task_id, update_data=task_data)
    
    def _update_google_task(self, task_id: str, update_data: dict) -> None:
        self._google_task_list.update_google_task(
            task_id,
            data=update_data
        )

    def _upload_notion_item_to_google_item(self, notion_item_id: str, item: dict) -> None:
        title = item['props'][self._notion.title_prop_name].value
        self._google_task_list.add_task_to_google_task_list(
            title, notion_item_id, None, False, False
        )


if __name__ == '__main__':
    notion = NotionDatabase(
        config.NOTION_DATABASE_ID,
        config.NOTION_TOKEN,
        config.NOTION_TITLE_PROP_NAME
    )
    google_tasks = GoogleTaskList(
        config.GOOGLE_TASK_LIST_ID
    )
    syncer = NotionTasksSynchronizer(notion, google_tasks)

    while True:
        syncer.sync()
        time.sleep(10)
