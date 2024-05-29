import datetime

from pydantic import dataclasses


@dataclasses.dataclass(slots=True)
class Token:
    access_token: str
    token_type: str
    expired_in: datetime.datetime
