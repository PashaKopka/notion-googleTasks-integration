from fastapi import APIRouter, Body, Depends, Form, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from logger import get_logger
from models.models import SyncingServices
from models.models import User as UserDB
from models.models import get_db
from services.google_tasks.google_tasks_profiler import GTasksProfiler
from services.notion.notion_profiler import NotionProfiler
from utils.crypt_utils import generate_access_token, validate_token, verify_password
from utils.pydantic_class import User

router = APIRouter()
logger = get_logger(__name__)


@router.get("/user_data")
async def get_user_data(
    user: User = Depends(validate_token),
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"Getting user data for {user.email}")

    syncing_service = await SyncingServices.get_service_by_user_id(user.id, db)
    if not syncing_service:
        return {"username": user.email, "is_syncing_service_ready": False}

    try:
        notion_profiler = NotionProfiler(
            syncing_service.service_notion_data["access_token"],
        )
        dbs = notion_profiler.get_lists()
    except Exception as e:
        logger.error(f"Error while getting notion data for user {user.email}: {e}")
        dbs = []

    try:
        google_tasks_profiler = GTasksProfiler(
            syncing_service.service_google_tasks_data,
        )
        lists = google_tasks_profiler.get_lists()
    except Exception as e:
        logger.error(f"Error while getting google data for user {user.email}: {e}")
        lists = []

    notion_data = syncing_service.service_notion_data or {}
    google_data = syncing_service.service_google_tasks_data or {}

    is_ready = await syncing_service.ready_to_start_sync(db)

    return {
        "username": user.email,
        "is_ready": is_ready,
        "is_syncing_service_ready": syncing_service.ready,
        "is_active": syncing_service.is_active,
        "options": {
            "notion": {
                "is_connected": bool(notion_data),
                "chosed_list": notion_data.get("duplicated_template_id"),
                "title_prop_name": notion_data.get("title_prop_name"),
                "available_lists": dbs,
            },
            "google_tasks": {
                "is_connected": bool(google_data),
                "available_lists": lists,
                "chosed_list": google_data.get("tasks_list_id"),
            },
        },
    }


@router.post("/user_data")
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

    await SyncingServices.update(
        user_id=user.id,
        values={
            "service_google_tasks_data": google_tasks_data,
            "service_notion_data": notion_data,
        },
        db=db,
    )

    return {}


@router.post("/register")
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


@router.post("/token")
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
