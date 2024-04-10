from typing import Optional, Dict
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from models.models import create_tables
from models.models import get_db

app = FastAPI()


class User(BaseModel):
    id: UUID
    email: str
    password: str


class SyncingServices(BaseModel):
    user_id: UUID
    id: UUID = Field(default_factory=uuid4)
    service_1_data: Dict
    service_2_data: Dict


class SyncingIds(BaseModel):
    user_id: UUID
    syncing_service_id: UUID
    notion_id: Optional[str]
    google_task_id: Optional[str]


@app.post("/signup/", response_model=User)
def signup(user: User, db: Session = Depends(get_db)):
    pass


@app.post("/login/", response_model=User)
def login(user: User, db: Session = Depends(get_db)):
    pass


@app.post("/sync_services/", response_model=SyncingServices)
def create_sync_services(
    syncing_services: SyncingServices, db: Session = Depends(get_db)
):
    pass


@app.post("/users/", response_model=User)
def create_user(user: User, db: Session = Depends(get_db)):
    return create_user(db, user)


if __name__ == "__main__":
    create_tables()
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
