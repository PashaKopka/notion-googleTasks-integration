import asyncio
import datetime

import pytest
from aioresponses import aioresponses

from models.models import SyncedItem, SyncingService, User
from services.notion.notion_db import NotionDB
from services.service import Item

pytest_plugins = ("pytest_asyncio",)

DATETIME = datetime.datetime(2021, 10, 10, 10, 10, 10, 10)
DATABASE_ID = "database_id"
TOKEN = "token"
TITLE_PROP_NAME = "Name"
DATABASE_URL_FORMAT = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
CREATE_PAGE_URL = f"https://api.notion.com/v1/pages"
PAGE_URL_FORMAT = "https://api.notion.com/v1/pages/{}"


@pytest.fixture
def item():
    return Item(
        name="name",
        status=True,
        google_task_id="google_task_id",
        notion_id="notion_id",
        updated_at=DATETIME,
    )


@pytest.fixture
def item_data(item):
    return {
        "object": "page",
        "id": item.notion_id,
        "parent": {"type": "database_id", "database_id": DATABASE_ID},
        "properties": {
            "Checkbox": {"checkbox": item.status},
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": item.name,
                        },
                        "plain_text": item.name,
                    }
                ]
            },
        },
    }


@pytest.fixture
async def user(db):
    user = User(email="test_notion_db@test.com", password="password")
    yield await user.save(db)
    await user.delete(db)


@pytest.fixture
async def syncing_service(db, user):
    syncing_service = SyncingService(
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
async def notion_db(db, syncing_service):
    notion_db = NotionDB(
        syncing_service_id=syncing_service.id,
        database_id=DATABASE_ID,
        token=TOKEN,
        title_prop_name=TITLE_PROP_NAME,
        db=db,
    )
    return notion_db


async def test_save_sync_ids(notion_db, item, db):
    await notion_db._save_sync_ids(item)
    db_item = await SyncedItem.get_by_sync_id(db, notion_id=item.notion_id)
    assert db_item is not None
    await db_item.delete(db)


async def test_add_item(notion_db, item, item_data, db):
    with aioresponses() as m:
        m.post(CREATE_PAGE_URL, payload={"id": item.notion_id})

        result = await notion_db.add_item(item)
        assert result is None
        m.assert_called_once_with(
            CREATE_PAGE_URL,
            method="POST",
            data=None,
            headers=notion_db._headers,
            json=item_data,
        )

    # Check if item is stored in the database
    db_item = await SyncedItem.get_by_sync_id(db, notion_id=item.notion_id)
    assert db_item is not None
    await db_item.delete(db)


async def test_update_item(notion_db, item, item_data):
    with aioresponses() as m:
        m.patch(PAGE_URL_FORMAT.format(item.notion_id), payload={"some": "data"})

        result = await notion_db.update_item(item)
        assert result == {"some": "data"}
        m.assert_called_once_with(
            PAGE_URL_FORMAT.format(item.notion_id),
            data=None,
            method="PATCH",
            headers=notion_db._headers,
            json=item_data,
        )


async def test_get_item_by_id(notion_db, item, item_data):
    item_data.update({"last_edited_time": DATETIME.isoformat()})
    with aioresponses() as m:
        m.get(
            PAGE_URL_FORMAT.format(item.notion_id),
            payload=item_data,
        )

        result = await notion_db.get_item_by_id(item.notion_id)
        assert result == item
        m.assert_called_once_with(
            PAGE_URL_FORMAT.format(item.notion_id),
            method="GET",
            headers=notion_db._headers,
        )


async def test_get_all_items(notion_db, item, item_data):
    item_data.update({"last_edited_time": DATETIME.isoformat()})
    with aioresponses() as m:
        m.post(DATABASE_URL_FORMAT, payload={"results": [item_data]})

        result = await notion_db.get_all_items()
        assert result == [item]
        m.assert_called_once_with(
            DATABASE_URL_FORMAT,
            method="POST",
            headers=notion_db._headers,
        )
