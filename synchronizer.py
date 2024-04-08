from abc import ABC, abstractmethod
import asyncio
import time
import config

from models.models import SyncedItem
from services.google_tasks.google_tasks import GTasksList
from services.notion.notion_db import NotionDB
from services.service import Item


class Synchronizer(ABC):

    @abstractmethod
    def sync(self):
        """
        Sync 2 services data.
        Algorithm:
        1. Get data from service 1
        2. Get data from service 2
        3. Compare data from service 1 and service 2 to find not synced data, or updated data
        4. Update data in service 1
        5. Update data in service 2
        6. Add new data to service 1 and get ids from it
        7. Add new data to service 2 and get ids from it
        8. Update data in service 1 with new ids from service 2
        9. Update data in service 2 with new ids from service 1
        """
        raise NotImplementedError


class NotionTasksSynchronizer(Synchronizer):

    def __init__(
        self,
        notion_service: NotionDB,
        google_tasks_service: GTasksList
    ) -> None:
        super().__init__()

        self._google_task_list = google_tasks_service
        self._notion_db = notion_service

    async def sync(self):
        notion_rows = await self._get_notion_rows()
        google_tasks_list = await self._get_google_tasks_list()

        # compare notion_rows and google_tasks_list
        (
            google_tasks_add_list,
            google_tasks_update_list,
            notion_rows_add_list,
            notion_rows_update_list
        ) = self._compare(notion_rows, google_tasks_list)

        asyncio.create_task(self._update_google_tasks(
            google_tasks_add_list,
            google_tasks_update_list
        ))
        asyncio.create_task(self._update_notion_rows(
            notion_rows_add_list,
            notion_rows_update_list
        ))

    async def _get_notion_rows(self) -> list[Item]:
        items = await self._notion_db.get_all_items()
        for item in items:
            synced_item = SyncedItem.get_by_sync_id(notion_id=item.notion_id)
            if synced_item:
                item.google_task_id = synced_item.google_task_id
        
        return items

    async def _get_google_tasks_list(self) -> list[Item]:
        items = await self._google_task_list.get_all_items()
        for item in items:
            synced_item = SyncedItem.get_by_sync_id(google_task_id=item.google_task_id)
            if synced_item:
                item.notion_id = synced_item.notion_id
        
        return items

    def _compare(
        self,
        notion_rows: list[Item],
        google_tasks_list: list[Item]
    ) -> tuple[list[Item]]:
        new_items_notion = filter(lambda x: x.notion_id == '', google_tasks_list)
        new_items_google = filter(lambda x: x.google_task_id == '', notion_rows)

        synced_items_google = filter(lambda x: x.notion_id != '', google_tasks_list)

        notion_rows_update_list = []
        google_tasks_update_list = []

        for item in synced_items_google:
            notion_item = next(
                filter(lambda x: x.notion_id == item.notion_id, notion_rows), None)
            if notion_item != item:
                # compare them by update time
                if notion_item.updated_at < item.updated_at:
                    # google task is newer
                    notion_rows_update_list.append(item)
                else:
                    # notion row is newer
                    google_tasks_update_list.append(notion_item)

        return (
            new_items_google,
            google_tasks_update_list,
            new_items_notion,
            notion_rows_update_list
        )

    async def _update_google_tasks(
        self,
        google_tasks_add_list: list[Item],
        google_tasks_update_list: list[Item]
    ):
        for item in google_tasks_add_list:
            asyncio.create_task(self._google_task_list.add_item(item))

        for item in google_tasks_update_list:
            asyncio.create_task(self._google_task_list.update_item(item))

    async def _update_notion_rows(
        self,
        notion_rows_add_list: list[Item],
        notion_rows_update_list: list[Item]
    ):
        for item in notion_rows_add_list:
            asyncio.create_task(self._notion_db.add_item(item))

        for item in notion_rows_update_list:
            asyncio.create_task(self._notion_db.update_item(item))


async def main():
    notion = NotionDB(
        "234",
        config.NOTION_DATABASE_ID,
        config.NOTION_TOKEN,
        config.NOTION_TITLE_PROP_NAME,
    )
    google_tasks = GTasksList(
        "234",
        config.GOOGLE_CLIENT_SECRET_FILE,
        config.GOOGLE_TASK_LIST_ID
    )
    syncer = NotionTasksSynchronizer(
        notion_service=notion,
        google_tasks_service=google_tasks
    )
    while True:
        await syncer.sync()
        await asyncio.sleep(20)


if __name__ == '__main__':
    asyncio.run(main())
