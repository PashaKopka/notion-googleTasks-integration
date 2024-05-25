import asyncio

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from logger import get_logger
from models.models import SyncingServices, get_db
from schemas.user import User
from services.google_tasks.google_tasks import GTasksList
from services.notion.notion_db import NotionDB
from synchronizer import NotionTasksSynchronizer
from utils.crypt_utils import validate_token

router = APIRouter()
logger = get_logger(__name__)


async def start_sync_notion_google_tasks(
    syncing_service_id: str,
    notion_data: dict,
    google_data: dict,
    db: AsyncSession,
):
    logger.info(f"Starting sync for service {syncing_service_id}")
    notion_db = NotionDB(
        syncing_service_id=syncing_service_id,
        database_id=notion_data["duplicated_template_id"],
        token=notion_data["access_token"],
        title_prop_name=notion_data["title_prop_name"],
        db=db,
    )
    google_tasks = GTasksList(
        syncing_service_id=syncing_service_id,
        client_config=google_data,
        db=db,
    )
    syncer = NotionTasksSynchronizer(
        notion_service=notion_db,
        google_tasks_service=google_tasks,
        db=db,
    )
    while True:
        await syncer.sync()
        await asyncio.sleep(10)


async def restart_sync():
    db_gen = get_db()
    db = await db_gen.asend(None)

    services = await SyncingServices.get_ready_services(db)
    logger.info(f"Restarting sync for {len(services)} services")
    for service in services:
        notion_data = service.service_notion_data
        google_data = service.service_google_tasks_data
        task = asyncio.create_task(
            start_sync_notion_google_tasks(
                syncing_service_id=service.id,
                notion_data=notion_data,
                google_data=google_data,
                db=db,
            )
        )
        logger.info(f"Restarted sync for service {service.id} with task_id {id(task)}")


@router.post("/start_sync", status_code=status.HTTP_201_CREATED)
async def start_sync(
    user: User = Depends(validate_token),
    db: AsyncSession = Depends(get_db),
):
    service = await SyncingServices.get_service_by_user_id(user.id, db)
    if not service or not await service.ready_to_start_sync(db):
        return {"error": "Not all services are connected"}

    notion_data = service.service_notion_data
    google_data = service.service_google_tasks_data
    task = asyncio.create_task(
        start_sync_notion_google_tasks(
            syncing_service_id=service.id,
            notion_data=notion_data,
            google_data=google_data,
            db=db,
        )
    )

    await SyncingServices.update(
        user_id=user.id,
        values={"is_active": True, "task_id": str(id(task))},
        db=db,
    )

    logger.info(f"User {user.email} started sync with task_id {id(task)}")


@router.post("/stop_sync", status_code=status.HTTP_204_NO_CONTENT)
async def stop_sync(
    user: User = Depends(validate_token),
    db: AsyncSession = Depends(get_db),
):
    service = await SyncingServices.get_service_by_user_id(user.id, db)
    task_id = service.task_id
    tasks = asyncio.all_tasks()
    for task in tasks:
        if str(id(task)) == task_id:
            task.cancel()
            logger.info(f"User {user.email} stopped sync with task_id {id(task)}")
            break

    # either way task is stopped or dont exists at all
    # so we can update service
    await SyncingServices.update(
        user_id=user.id,
        values={"is_active": False, "task_id": None},
        db=db,
    )
