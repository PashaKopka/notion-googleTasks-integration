import base64
import json
from typing import Optional, Dict
from uuid import UUID, uuid4
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from fastapi import FastAPI, Depends
import requests
from sqlalchemy.orm import Session

from config import (
    HOST,
    NOTION_AUTHORIZATION_URL,
    NOTION_OAUTH_CLIENT_ID,
    NOTION_OAUTH_CLIENT_SECRET,
    NOTION_TOKEN_URL,
)
from models.models import SyncingServices, create_tables, get_db

app = FastAPI()


class User(BaseModel):
    id: UUID
    email: str
    password: str


class SyncingIds(BaseModel):
    user_id: UUID
    syncing_service_id: UUID
    notion_id: Optional[str]
    google_task_id: Optional[str]


def encode(data: str | dict) -> str:
    if isinstance(data, dict):
        data = json.dumps(data)
        encoded_data = data.encode("utf-8")
    elif isinstance(data, str):
        encoded_data = data.encode("utf-8")

    b64_encoded_data = base64.b64encode(encoded_data)
    return b64_encoded_data.decode("utf-8")


def decode_dict(data: str) -> dict:
    utf_8_encoded_data = data.encode("utf-8")
    b64_decoded_data = base64.b64decode(utf_8_encoded_data)
    decoded_data = b64_decoded_data.decode("utf-8")
    return json.loads(decoded_data)


def get_notion_data(code: str):
    encoded_credentials = encode(
        f"{NOTION_OAUTH_CLIENT_ID}:{NOTION_OAUTH_CLIENT_SECRET}"
    )
    response = requests.post(
        NOTION_TOKEN_URL,
        data={
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": f"{HOST}/notion/",
        },
        headers={
            "Authorization": f"Basic {encoded_credentials}",
        },
    )
    return response.json()


@app.post("/signup/", response_model=User)
def signup(user: User, db: Session = Depends(get_db)):
    pass


@app.post("/login/", response_model=User)
def login(user: User, db: Session = Depends(get_db)):
    pass


@app.post("/users/", response_model=User)
def create_user(user: User, db: Session = Depends(get_db)):
    return create_user(db, user)


@app.get("/notion/")
def save_notion_connection(code: str, state: str):
    user_data = decode_dict(state)
    notion_data = get_notion_data(code)
    services = SyncingServices(
        user_id=user_data["user_id"],
        service_notion_data=notion_data,
    )
    services.save()


@app.get("/notion/connect")
def connect_notion():
    # Get user if by given token
    # encode json with {user_id: user_id}
    user_id = "a25fa2ac-dfd2-468a-9833-630bd7fb8b0c"
    data = encode({"user_id": user_id})
    return RedirectResponse(f"{NOTION_AUTHORIZATION_URL}&state={data}")


if __name__ == "__main__":
    create_tables()
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
