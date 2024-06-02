import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from models.models import SyncedItem
from services.google_tasks.google_tasks import GTasksList
from schemas.Item import Item
from services.notion.notion_db import NotionDB
from synchronizers.synchronizer import Synchronizer


class NotionTasksSynchronizer(Synchronizer):

    def __init__(
        self,
        notion_service: NotionDB,
        google_tasks_service: GTasksList,
        db: AsyncSession,
    ) -> None:
        super().__init__()

        self._google_task_list = google_tasks_service
        self._notion_db = notion_service
        self._db = db

    async def sync(self):
        notion_rows, google_tasks_list = await asyncio.gather(
            self._get_notion_rows(), self._get_google_tasks_list()
        )

        # compare notion_rows and google_tasks_list
        (
            google_tasks_add_list,
            google_tasks_update_list,
            notion_rows_add_list,
            notion_rows_update_list,
        ) = self._compare(notion_rows, google_tasks_list)

        asyncio.create_task(
            self._update_google_tasks(google_tasks_add_list, google_tasks_update_list)
        )
        asyncio.create_task(
            self._update_notion_rows(notion_rows_add_list, notion_rows_update_list)
        )

    async def _get_notion_rows(self) -> list[Item]:
        items = await self._notion_db.get_all_items()
        for item in items:
            synced_item = await SyncedItem.get_by_sync_id(
                notion_id=item.notion_id, db=self._db
            )
            if synced_item:
                item.google_task_id = synced_item.google_task_id

        return items

    async def _get_google_tasks_list(self) -> list[Item]:
        items = await self._google_task_list.get_all_items() or []
        for item in items:
            synced_item = await SyncedItem.get_by_sync_id(
                google_task_id=item.google_task_id, db=self._db
            )
            if synced_item:
                item.notion_id = synced_item.notion_id

        return items

    def _compare(
        self, notion_rows: list[Item], google_tasks_list: list[Item]
    ) -> tuple[list[Item]]:
        new_items_notion = filter(lambda x: not x.notion_id, google_tasks_list)
        new_items_google = filter(lambda x: not x.google_task_id, notion_rows)

        synced_items_google = filter(lambda x: x.notion_id != "", google_tasks_list)

        notion_rows_update_list = []
        google_tasks_update_list = []

        for item in synced_items_google:
            notion_item = next(
                filter(lambda x: x.notion_id == item.notion_id, notion_rows), None
            )
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
            notion_rows_update_list,
        )

    async def _update_google_tasks(
        self, google_tasks_add_list: list[Item], google_tasks_update_list: list[Item]
    ):
        for item in google_tasks_add_list:
            asyncio.create_task(self._google_task_list.add_item(item))

        for item in google_tasks_update_list:
            asyncio.create_task(self._google_task_list.update_item(item))

    async def _update_notion_rows(
        self, notion_rows_add_list: list[Item], notion_rows_update_list: list[Item]
    ):
        for item in notion_rows_add_list:
            asyncio.create_task(self._notion_db.add_item(item))

        for item in notion_rows_update_list:
            asyncio.create_task(self._notion_db.update_item(item))
