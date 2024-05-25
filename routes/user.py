from fastapi import APIRouter, Body, Depends, Form, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from logger import get_logger
from models.models import SyncingServices
from models.models import User as UserDB
from models.models import get_db
from schemas.auth import Token
from schemas.user import User
from schemas.user_data import GoogleTasksOptions, NotionOptions, Options, UserData
from services.google_tasks.google_tasks_profiler import GTasksProfiler
from services.notion.notion_profiler import NotionProfiler
from utils.crypt_utils import generate_access_token, validate_token, verify_password

router = APIRouter()
logger = get_logger(__name__)


def get_notion_dbs(syncing_service):
    try:
        notion_profiler = NotionProfiler(
            syncing_service.service_notion_data["access_token"],
        )
        return notion_profiler.get_lists()
    except Exception as e:
        logger.error(
            f"Error while getting notion data for syncing_service {syncing_service.id}: {e}"
        )
        return {}


def get_google_tasks_lists(syncing_service):
    try:
        google_tasks_profiler = GTasksProfiler(
            syncing_service.service_google_tasks_data,
        )
        return google_tasks_profiler.get_lists()
    except Exception as e:
        logger.error(
            f"Error while getting google data for syncing_service {syncing_service.id}: {e}"
        )
        return {}


async def generate_user_data(user, syncing_service, db):
    dbs = get_notion_dbs(syncing_service)
    lists = get_google_tasks_lists(syncing_service)

    if not dbs:
        # if dbs is empty, it means that there was an error while getting notion data
        # so we show that user is not connected to notion
        notion_data = {}
    else:
        notion_data = syncing_service.service_notion_data or {}

    if not lists:
        # if lists is empty, it means that there was an error while getting google data
        # so we show that user is not connected to google tasks
        google_data = {}
    else:
        google_data = syncing_service.service_google_tasks_data or {}

    is_ready = await syncing_service.ready_to_start_sync(db)

    notion_options = NotionOptions(
        is_connected=bool(notion_data),
        chosed_list=notion_data.get("duplicated_template_id"),
        title_prop_name=notion_data.get("title_prop_name"),
        available_lists=dbs,
    )
    google_options = GoogleTasksOptions(
        is_connected=bool(google_data),
        available_lists=lists,
        chosed_list=google_data.get("tasks_list_id"),
    )
    options = Options(
        notion=notion_options,
        google_tasks=google_options,
    )
    result = UserData(
        username=user.email,
        is_ready=is_ready,
        is_syncing_service_ready=syncing_service.ready,
        is_active=syncing_service.is_active,
        options=options,
    )

    return result


@router.get("/user_data", response_model=UserData)
async def get_user_data(
    user: User = Depends(validate_token),
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"Getting user data for {user.email}")

    syncing_service = await SyncingServices.get_service_by_user_id(user.id, db)
    if not syncing_service:
        return {"username": user.email, "is_syncing_service_ready": False}

    return await generate_user_data(user, syncing_service, db)


@router.post("/user_data", status_code=status.HTTP_201_CREATED, response_model=UserData)
async def save_user_data(
    user: User = Depends(validate_token),
    google_tasks_list_id: str = Body(None),
    notion_list_id: str = Body(None),
    notion_title_prop_name: str = Body(None),
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"Saving user data for {user.email}")

    syncing_service = await SyncingServices.get_service_by_user_id(user.id, db)
    if not syncing_service:
        return {"error": "Syncing service not found"}

    google_tasks_data = syncing_service.service_google_tasks_data
    notion_data = syncing_service.service_notion_data

    if google_tasks_list_id:
        google_tasks_data["tasks_list_id"] = google_tasks_list_id
    if notion_list_id:
        notion_data["duplicated_template_id"] = notion_list_id
    if notion_title_prop_name:
        notion_data["title_prop_name"] = notion_title_prop_name

    service = await SyncingServices.update(
        user_id=user.id,
        values={
            "service_google_tasks_data": google_tasks_data,
            "service_notion_data": notion_data,
        },
        db=db,
    )
    return service


@router.post("/register", response_model=Token)
async def register(
    username: str = Form(None),
    password: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    if not username or not password:
        raise HTTPException(
            status_code=400, detail="Username and password are required"
        )
    user = UserDB(
        email=username,
        password=password,
    )
    await user.save(db)

    logger.info(f"User {username} registered, id {user.id}")
    access_token, expired_in = generate_access_token(user)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expired_in": expired_in,
    }


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await UserDB.get_by_email(form_data.username, db)
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token, expired_in = generate_access_token(user)
    logger.info(f"User {user.email} logged in")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expired_in": expired_in,
    }
