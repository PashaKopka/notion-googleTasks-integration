from abc import ABC, abstractmethod


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
