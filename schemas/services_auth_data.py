from typing import Any

from pydantic import dataclasses


@dataclasses.dataclass(slots=True)
class NotionAuthData:
    access_token: str
    duplicated_template_id: str
    data: dict[str, Any]


@dataclasses.dataclass(slots=True)
class GoogleAuthData:
    token: str
    refresh_token: str
    token_uri: str
    client_id: str
    client_secret: str
    data: dict[str, Any]
