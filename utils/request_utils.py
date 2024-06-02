from uuid import uuid4

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config import REDIS_URL
from logger import get_logger
from models.models import User as UserDB
from models.models import get_db
from redis_client import RedisClient
from schemas.user import User

redis = RedisClient(REDIS_URL)
logger = get_logger(__name__)


def set_user_to_session(user: User) -> str:
    state_key = str(uuid4())
    logger.info(f"Set user {user.email} to session")
    redis.set(state_key, user.id)
    return state_key


async def get_user_from_session(
    state: str,
    db: AsyncSession = Depends(get_db),
) -> UserDB:
    user_id = redis.get(state)
    if user_id is None:
        logger.error(f"Invalid state: {state}")
        raise HTTPException("Invalid state")

    user = await UserDB.get_by_id(user_id, db)
    if user is None:
        logger.error(f"User not found: {user_id}")
        raise HTTPException("User not found")

    return user
