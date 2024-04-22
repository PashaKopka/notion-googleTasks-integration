from collections import defaultdict
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel

from models.models import User as UserDB


class User(BaseModel):
    id: str
    email: str
    password: str


def get_user(
    id_: str = "",
    email: str = "",
    *args,
) -> Optional[User]:
    if args:
        raise ValueError("Only keyword arguments are allowed")
    if id_:
        user: UserDB = UserDB.get_by_id(id_)
    elif email:
        user: UserDB = UserDB.get_by_email(email)
    if user:
        return User(
            id=user.id,
            email=user.email,
            password=user.password,
        )
    return None


def get_user_by_session_state(session: defaultdict):
    def get_user_from_session(state: str):
        try:
            user_id = session["state"].pop(state)["user_id"]
        except KeyError:
            raise HTTPException(status_code=400, detail="Invalid state")
        user = get_user(id_=user_id)
        return user

    return get_user_from_session


def set_user_by_session_state(session: defaultdict):
    def set_user_to_session(user: User):
        state = str(hash(user.email))
        session["state"][state] = {"user_id": user.id}
        return state

    return set_user_to_session
