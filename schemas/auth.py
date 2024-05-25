import datetime

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str
    expired_in: datetime.datetime
