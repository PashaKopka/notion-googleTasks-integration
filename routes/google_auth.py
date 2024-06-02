import json
from typing import Literal
from urllib.parse import urljoin, urlparse, urlunparse

import google_auth_oauthlib
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from config import GOOGLE_API_SCOPES, GOOGLE_CLIENT_SECRET_FILE, HOST
from logger import get_logger
from models.models import get_db
from schemas.user import User
from utils.db_utils import validate_token
from utils.request_utils import get_user_from_session, set_user_to_session
from utils.routes_utils import create_or_update_syncing_service

router = APIRouter()
logger = get_logger(__name__)
BASE_URL = urljoin(HOST, "/google_tasks")

from main import redirect_to_home


def get_google_task_data(credentials):
    return json.loads(credentials.to_json())


def absolute_url_for(url_name: str, base_url: str = BASE_URL):
    redirect_path = router.url_path_for(url_name)
    return redirect_path.make_absolute_url(base_url=base_url)


def change_schema(url: str, scheme: Literal["http", "https"] = "https") -> str:
    original_url = url
    parsed_url = urlparse(original_url)
    new_url = parsed_url._replace(scheme="https")
    authorization_response = urlunparse(new_url)
    return authorization_response


@router.get("/")
async def save_google_connection(
    state: str,
    code: str,
    scope: str,
    request: Request,
    user: User = Depends(get_user_from_session),
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"User {user.email} save Google Tasks connection")

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRET_FILE, scopes=[scope], state=state
    )
    redirect_path = router.url_path_for("save_google_connection")
    flow.redirect_uri = str(redirect_path.make_absolute_url(base_url=BASE_URL))

    authorization_response = change_schema(str(request.url), "https")

    flow.fetch_token(authorization_response=authorization_response)
    credentials = get_google_task_data(flow.credentials)

    await create_or_update_syncing_service(
        user_id=user.id,
        google_tasks_data=credentials,
        db=db,
    )

    logger.info(f"User {user.email} connected Google Tasks")
    return redirect_to_home


@router.get("/connect")
async def connect_google_tasks(user: User = Depends(validate_token)):
    logger.info(f"User {user.email} start connecting Google Tasks")

    state = set_user_to_session(user)

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRET_FILE, scopes=GOOGLE_API_SCOPES, state=state
    )
    flow.redirect_uri = absolute_url_for("save_google_connection")

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
    )
    logger.info(
        f"User {user.email} redirect to Google Tasks authorization page {authorization_url}"
    )
    return {authorization_url}
