import requests
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from config import (
    HOST,
    NOTION_AUTHORIZATION_URL,
    NOTION_OAUTH_CLIENT_ID,
    NOTION_OAUTH_CLIENT_SECRET,
    NOTION_TITLE_PROP_NAME,
    NOTION_TOKEN_URL,
)
from logger import get_logger
from models.models import get_db
from utils.routes_utils import create_or_update_syncing_service
from schemas.user import User
from utils.crypt_utils import encode, validate_token
from utils.request_utils import get_user_by_session_state, set_user_by_session_state

router = APIRouter()
logger = get_logger(__name__)

from main import SESSION, redirect_to_home

get_user_from_session = get_user_by_session_state(SESSION)
set_user_to_session = set_user_by_session_state(SESSION)


def get_notion_data(code: str):
    encoded_credentials = encode(
        f"{NOTION_OAUTH_CLIENT_ID}:{NOTION_OAUTH_CLIENT_SECRET}"
    )

    logger.info(f"Getting Notion data from code {code}")
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


@router.get("/")
async def save_notion_connection(
    code: str,
    user: User = Depends(get_user_from_session),
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"User {user.email} save Notion connection")

    notion_data = get_notion_data(code)
    notion_data["title_prop_name"] = NOTION_TITLE_PROP_NAME
    await create_or_update_syncing_service(
        user_id=user.id,
        notion_data=notion_data,
        db=db,
    )

    logger.info(f"User {user.email} connected Notion")
    return redirect_to_home


@router.get("/connect")
def connect_notion(user: User = Depends(validate_token)):
    logger.info(f"User {user.email} start connecting Notion")

    state = set_user_to_session(user)
    return {f"{NOTION_AUTHORIZATION_URL}&state={state}"}
