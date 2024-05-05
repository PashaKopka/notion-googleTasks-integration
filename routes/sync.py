import asyncio

from fastapi import APIRouter, Depends

from models.models import SyncingServices
from services.google_tasks.google_tasks import GTasksList
from services.notion.notion_db import NotionDB
from synchronizer import NotionTasksSynchronizer
from utils.crypt_utils import validate_token
from utils.pydantic_class import User

router = APIRouter()


async def start_sync_notion_google_tasks(
    syncing_service_id: str, notion_data: dict, google_data: dict
):
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


@router.post("/restart_sync")
async def restart_sync():
    # TODO maybe rework this
    services = SyncingServices.get_ready_services()
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

    return {}


@router.post("/start_sync")
async def start_sync(user: User = Depends(validate_token)):
    service = SyncingServices.get_service_by_user_id(user.id)
    if not service.ready_to_start_sync():
        return {"error": "Not all services are connected"}
    notion_data = service.service_notion_data
    google_data = service.service_google_tasks_data
    asyncio.create_task(
        start_sync_notion_google_tasks(
            syncing_service_id=service.id,
            notion_data=notion_data,
            google_data=google_data,
        )
    )
    return {}
