from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from models.models import SyncingServices
from models.models import User as UserDB
from services.google_tasks.google_tasks_profiler import GTasksProfiler
from services.notion.notion_profiler import NotionProfiler
from utils.crypt_utils import generate_access_token, validate_token, verify_password
from utils.pydantic_class import User

router = APIRouter()


@router.get("/user_data")
def get_user_data(user: User = Depends(validate_token)):
    syncing_service = SyncingServices.get_service_by_user_id(user.id)
    if not syncing_service:
        return {"username": user.email, "is_syncing_service_ready": False}
    notion_profiler = NotionProfiler(
        syncing_service.service_notion_data["access_token"],
    )
    google_tasks_profiler = GTasksProfiler(
        syncing_service.service_google_tasks_data,
    )
    lists = google_tasks_profiler.get_lists()
    dbs = notion_profiler.get_lists()
    return {
        "username": user.email,
        "is_syncing_service_ready": syncing_service.ready,
        "options": {
            "notion": {
                "is_connected": syncing_service.service_notion_data is not None,
                "chosed_list": syncing_service.service_notion_data[
                    "duplicated_template_id"
                ],
                "title_prop_name": syncing_service.service_notion_data.get(
                    "title_prop_name"
                ),
                "available_lists": dbs,
            },
            "google_tasks": {
                "is_connected": syncing_service.service_google_tasks_data is not None,
                "available_lists": lists,
                "chosed_list": syncing_service.service_google_tasks_data.get(
                    "tasks_list_id"
                ),
            },
        },
    }


@router.post("/user_data")
def save_user_data(
    user: User = Depends(validate_token),
    google_tasks_list_id: str = Body(None),
    notion_list_id: str = Body(None),
    notion_title_prop_name: str = Body(None),
):
    syncing_service = SyncingServices.get_service_by_user_id(user.id)
    if google_tasks_list_id:
        syncing_service.service_google_tasks_data["tasks_list_id"] = (
            google_tasks_list_id
        )
    if notion_list_id:
        syncing_service.service_notion_data["duplicated_template_id"] = notion_list_id
    if notion_title_prop_name:
        syncing_service.service_notion_data["title_prop_name"] = notion_title_prop_name

    syncing_service.update()

    return {}


@router.post("/register")
async def register(
    username: str = Body(None),
    password: str = Body(None),
):
    if not username or not password:
        raise HTTPException(
            status_code=400, detail="Username and password are required"
        )
    user = UserDB(
        email=username,
        password=password,
    )
    user.save()
    access_token, expired_in = generate_access_token(user)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expired_in": expired_in,
    }


@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = UserDB.get_by_email(form_data.username)
    if not user or verify_password(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token, expired_in = generate_access_token(user)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expired_in": expired_in,
    }
