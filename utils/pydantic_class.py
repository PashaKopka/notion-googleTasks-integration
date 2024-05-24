from pydantic import BaseModel


class User(BaseModel):
    id: str
    email: str
    password: str  # TODO move to schemas folder
