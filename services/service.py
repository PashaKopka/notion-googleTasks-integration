from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import datetime
from typing import Union


@dataclass
class Item:
    name: str
    status: bool
    updated_at: datetime = field(compare=False)

    # services
    notion_id: str = field(default="", compare=False)
    google_task_id: str = field(default="", compare=False)


class AbstractDataAdapter(ABC):

    @abstractmethod
    def dict_to_item(self, data: dict) -> Item:
        raise NotImplementedError

    @abstractmethod
    def item_to_dict(self, item: Item) -> dict:
        raise NotImplementedError

    @abstractmethod
    def dicts_to_items(self, data: list[dict]) -> list[Item]:
        raise NotImplementedError

    @abstractmethod
    def items_to_dicts(self, items: dict[Item]) -> list[dict]:
        raise NotImplementedError


class AbstractService(ABC):

    @abstractmethod
    def get_all_items(self) -> list[Item]:
        raise NotImplementedError

    @abstractmethod
    def get_item_by_id(self, item_id: str) -> Item:
        raise NotImplementedError

    @abstractmethod
    def update_item(self, item: Item) -> str:
        """Update item in service by id. Return id."""
        raise NotImplementedError

    @abstractmethod
    def add_item(self, data: Item) -> str:
        """Add item to service. Return id."""
        raise NotImplementedError

    @abstractmethod
    def _save_sync_ids(self, item: Item) -> None:
        raise NotImplementedError


class AbstractProfiler(ABC):

    def get_lists(self) -> list[dict]:
        raise NotImplementedError