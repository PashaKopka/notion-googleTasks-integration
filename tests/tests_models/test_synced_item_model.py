import datetime

import pytest

from models.models import SyncedItem, SyncingServices, User
from services.service import Item


@pytest.fixture
def item():
    return Item(
        name="name",
        status=True,
        google_task_id="google_task_id",
        notion_id="notion_id",
        updated_at=datetime.datetime(2021, 10, 10, 10, 10, 10, 10),
    )


@pytest.fixture
async def user(db):
    user = User(email="test_syncing_service_model@test.com", password="password")
    yield await user.save(db)
    await user.delete(db)


@pytest.fixture
async def syncing_service(db, user):
    syncing_service = SyncingServices(
        user_id=user.id,
        service_google_tasks_data={"tasks_list_id": "tasks_list_id"},
        service_notion_data={
            "duplicated_template_id": "duplicated_template_id",
            "title_prop_name": "title_prop_name",
        },
    )
    yield await syncing_service.save(db)
    await syncing_service.delete(db)


@pytest.fixture
async def synced_item(db, syncing_service, item):
    synced_item = SyncedItem(
        notion_id=item.notion_id,
        google_task_id=item.google_task_id,
        syncing_service_id=syncing_service.id,
    )
    yield await synced_item.save(db)
    await synced_item.delete(db)


async def test_synced_item_get_by_sync_id(synced_item, item, db):
    synced_item_db = await SyncedItem.get_by_sync_id(db, notion_id=item.notion_id)
    assert synced_item_db is not None
    assert synced_item_db.notion_id == synced_item.notion_id

    synced_item_db = await SyncedItem.get_by_sync_id(
        db, google_task_id=item.google_task_id
    )
    assert synced_item_db is not None
    assert synced_item_db.google_task_id == synced_item.google_task_id


async def test_synced_item_create_from_item(syncing_service, item):
    synced_item = SyncedItem.create_from_item(item, syncing_service.id)
    assert synced_item.notion_id == item.notion_id
    assert synced_item.google_task_id == item.google_task_id
    assert synced_item.syncing_service_id == syncing_service.id
