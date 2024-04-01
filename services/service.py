from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Union


@dataclass
class Item:
    name: str
    status: bool
    service_1_id: str
    service_2_id: str


class AbstractDataAdapter(ABC):
    
    def dict_to_item(self, data: dict) -> Item:
        raise NotImplementedError
    
    def item_to_dict(self, item: Item) -> dict:
        raise NotImplementedError
    
    def dicts_to_items(self, data: list[dict]) -> list[Item]:
        raise NotImplementedError
    
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
    def update_item(self, item_id: str, data: Item) -> str:
        """Update item in service by id. Return id."""
        raise NotImplementedError
    
    @abstractmethod
    def add_item(self, data: Item) -> str:
        """Add item to service. Return id."""
        raise NotImplementedError
