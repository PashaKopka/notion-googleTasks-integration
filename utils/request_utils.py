from collections import defaultdict

from fastapi import HTTPException

from models.models import User as UserDB
from utils.pydantic_class import User


def get_user_by_session_state(session: defaultdict):
    def get_user_from_session(state: str):
        try:
            user_id = session["state"].pop(state)["user_id"]
        except KeyError:
            raise HTTPException(status_code=400, detail="Invalid state")
        user = UserDB.get_by_id(user_id)
        return user

    return get_user_from_session


def set_user_by_session_state(session: defaultdict):
    def set_user_to_session(user: User):
        state = str(user.id)
        session["state"][state] = {"user_id": user.id}
        return state

    return set_user_to_session
