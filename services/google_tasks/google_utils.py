class GoogleTaskStatus:
    GOOGLE_TASK_STATUSES_STR_TO_BOOL = {
        'needsAction': False,
        'completed': True
    }
    GOOGLE_TASK_STATUSES_BOOL_TO_STR = {
        False: 'needsAction',
        True: 'completed'
    }
    
    def __init__(self, status: str | bool) -> None:
        if isinstance(status, str):
            self._status = self._str_to_bool(status)
        elif isinstance(status, bool):
            self._status = status
        elif isinstance(status, GoogleTaskStatus):
            self._status = status._status
        else:
            raise TypeError('Status must be str or bool or GoogleTaskStatus')
    
    def _str_to_bool(self, status: str) -> bool:
        return self.GOOGLE_TASK_STATUSES_STR_TO_BOOL[status]

    def __str__(self) -> str:
        return self.GOOGLE_TASK_STATUSES_BOOL_TO_STR[self._status]
    
    def __repr__(self) -> str:
        return self.GOOGLE_TASK_STATUSES_BOOL_TO_STR[self._status]
    
    def __bool__(self) -> bool:
        return self._status