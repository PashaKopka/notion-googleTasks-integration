from pydantic import dataclasses


@dataclasses.dataclass(slots=True)
class User:
    id: str
    email: str
    password: str
