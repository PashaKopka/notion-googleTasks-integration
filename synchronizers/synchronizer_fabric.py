from sqlalchemy.ext.asyncio import AsyncSession

from services.google_tasks.google_tasks import GTasksList
from services.notion.notion_db import NotionDB
from services.service import AbstractService
from synchronizers.notion_tasks_synchronizer import NotionTasksSynchronizer
from synchronizers.synchronizer import Synchronizer


class SynchronizerFabric:

    def __init__(self, *args: list[AbstractService]) -> None:
        self._services = args

    def get_synchronizer(self, db: AsyncSession) -> Synchronizer:
        if len(self._services) != 2:
            raise ValueError("Need 2 services to sync")

        service1, service2 = self._services

        if self._is_notion_tasks(service1, service2):
            return NotionTasksSynchronizer(service1, service2, db)
        else:
            raise ValueError("Unknown services")

    def _is_notion_tasks(self, service1, service2):
        return (
            isinstance(service1, NotionDB)
            and isinstance(service2, GTasksList)
            or isinstance(service2, NotionDB)
            and isinstance(service1, GTasksList)
        )
