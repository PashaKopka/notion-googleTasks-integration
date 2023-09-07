from datetime import datetime
import itertools


class DataRow:
    
    def __init__(
        self,
        id: str = None,
        sync_id: str = None,
        object_type: str = None,
        created_time: datetime = None,
        updated_time: datetime = None,
    ) -> None:
        self._id = id
        self._object_type = object_type
        self._created_time = created_time
        self._updated_time = updated_time
        self._sync_id = sync_id
        
        self._props = {}
    
    def add_prop(self, prop_name: str, prop) -> None:
        self._props[prop_name] = prop
    
    @property
    def id(self) -> str:
        return self._id

    @property
    def sync_id(self) -> str:
        return self._sync_id
    
    @property
    def object_type(self) -> str:
        return self._object_type
    
    @property
    def created_time(self) -> datetime:
        return self._created_time
    
    @property
    def updated_time(self) -> datetime:
        return self._updated_time
    
    @id.setter
    def id(self, value: str) -> None:
        self._id = value
    
    @sync_id.setter
    def sync_id(self, value: str) -> None:
        self._sync_id = value
    
    def props_as_dict(self):
        return {k: v for prop in self._props.values() for k, v in prop.deserialize().items()}
    
    @classmethod
    def filter_not_synced_rows(cls, rows: list, return_as_list: bool = False) -> tuple[iter, iter]:
        """
        Returns two iterators: first one contains not synced rows, second one contains synced rows
        """
        t1, t2 = itertools.tee(rows)
        i1, i2 = itertools.filterfalse(lambda x: x.sync_id, t1), filter(lambda x: x.sync_id, t2)
        
        if return_as_list:
            return list(i1), list(i2)
        return i1, i2
