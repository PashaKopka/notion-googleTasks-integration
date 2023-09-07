from abc import ABC, abstractmethod
import httpx

import requests

from data_row import DataRow


class AbstractDataRowAdapter(ABC):
    
    def dict_to_data_row(self, row: dict) -> DataRow:
        raise NotImplementedError
    
    def data_row_to_dict(self, data_row: DataRow) -> dict:
        raise NotImplementedError
    
    def dicts_to_data_rows(self, rows: list[dict]) -> list[DataRow]:
        raise NotImplementedError
    
    def data_rows_to_dicts(self, data_rows: dict[DataRow]) -> list[dict]:
        raise NotImplementedError


class AbstractService(ABC):
    
    @abstractmethod
    def get_data(self) -> list[DataRow]:
        raise NotImplementedError
    
    @abstractmethod
    def get_new_data(self) -> list[DataRow]:
        raise NotImplementedError
    
    @abstractmethod
    def update_data(self, data: list[DataRow]) -> bool:
        raise NotImplementedError
    
    @abstractmethod
    def _get_data_by_id(self, data_id: str) -> dict:
        raise NotImplementedError
    
    @abstractmethod
    def _get_data(self) -> list[dict]:
        raise NotImplementedError
    
    @abstractmethod
    def _get_new_data(self) -> list[dict]:
        raise NotImplementedError
    
    @abstractmethod
    def _update_data(self, data: list[DataRow]) -> bool:
        raise NotImplementedError

    @abstractmethod
    def _add_new_data(self, data: list[DataRow]) -> bool:
        raise NotImplementedError
    
    def __getitem__(self, notion_id: str) -> DataRow:
        raise NotImplementedError
    
    def _make_request(self, url: str, method: str = 'POST', data: dict = None) -> requests.Response:
        raise NotImplementedError
    
    async def _make_requests_async(
        self,
        url: str,
        method: str = 'POST',
        data: list[dict] = None
    ) -> list[httpx.Response]:
        raise NotImplementedError
