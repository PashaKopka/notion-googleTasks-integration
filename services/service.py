from abc import ABC, abstractmethod
from dataclasses import dataclass
import datetime
from typing import Union


@dataclass
class Item:
    name: str
    status: bool
    service_1_id: str
    service_2_id: str
    updated_at: datetime
    # TODO think about service_1 and service_2 names. This is bad naming.
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Item):
            return False
        return all([
            self.name == other.name,
            self.status == other.status,
            self.service_1_id == other.service_1_id,
            self.service_2_id == other.service_2_id
        ])
    
    def __ne__(self, other) -> bool:
        return not self.__eq__(other)


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
    
    @abstractmethod
    def _get_sync_id(self, item_id: str) -> str:
        raise NotImplementedError


class AbstractService(ABC):
    
    @abstractmethod
    def get_all_items(self) -> list[Item]:
        raise NotImplementedError
    
    @abstractmethod
    def get_item_by_id(self, item_id: str) -> Item:
        raise NotImplementedError
    
    @abstractmethod
    def update_item(self, item_id: str, data: Item) -> str:
        """Update item in service by id. Return id."""
        raise NotImplementedError
    
    @abstractmethod
    def add_item(self, data: Item) -> str:
        """Add item to service. Return id."""
        raise NotImplementedError
    
    @abstractmethod
    def _save_sync_ids(self, item: Item) -> None:
        raise NotImplementedError
