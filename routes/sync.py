import asyncio

from fastapi import APIRouter, Depends

from logger import get_logger
from models.models import SyncingServices
from services.google_tasks.google_tasks import GTasksList
from services.notion.notion_db import NotionDB
from synchronizer import NotionTasksSynchronizer
from utils.crypt_utils import validate_token
from utils.pydantic_class import User

router = APIRouter()
logger = get_logger(__name__)


async def start_sync_notion_google_tasks(
    syncing_service_id: str, notion_data: dict, google_data: dict
):
    logger.info(f"Starting sync for service {syncing_service_id}")
    notion_db = NotionDB(
        syncing_service_id=syncing_service_id,
        database_id=notion_data["duplicated_template_id"],
        token=notion_data["access_token"],
        title_prop_name=notion_data["title_prop_name"],
    )
    google_tasks = GTasksList(
        syncing_service_id=syncing_service_id,
        client_config=google_data,
        tasks_list_id="YTBIeks1amJKQUJLdnVqcg",
    )
    syncer = NotionTasksSynchronizer(
        notion_service=notion_db,
        google_tasks_service=google_tasks,
    )
    while True:
        await syncer.sync()
        await asyncio.sleep(10)


async def restart_sync():
    services = SyncingServices.get_ready_services()
    logger.info(f"Restarting sync for {len(services)} services")
    for service in services:
        notion_data = service.service_notion_data
        google_data = service.service_google_tasks_data
        asyncio.create_task(
            start_sync_notion_google_tasks(
                syncing_service_id=service.id,
                notion_data=notion_data,
                google_data=google_data,
            )
        )


@router.post("/start_sync")
async def start_sync(user: User = Depends(validate_token)):
    service = SyncingServices.get_service_by_user_id(user.id)
    if not service.ready_to_start_sync():
        return {"error": "Not all services are connected"}
    notion_data = service.service_notion_data
    google_data = service.service_google_tasks_data
    task = asyncio.create_task(
        start_sync_notion_google_tasks(
            syncing_service_id=service.id,
            notion_data=notion_data,
            google_data=google_data,
        )
    )
    logger.info(f"User {user.email} started sync with task_id {id(task)}")
    return {"task_id": id(task)}
