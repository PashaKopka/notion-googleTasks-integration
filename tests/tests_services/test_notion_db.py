import asyncio
import datetime

import pytest
from aioresponses import aioresponses

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
def notion_db():
    return NotionDB(
        syncing_service_id="syncing_service_id",
        database_id=DATABASE_ID,
        token=TOKEN,
        title_prop_name=TITLE_PROP_NAME,
    )


@pytest.fixture(autouse=True)
def mock_save_sync_ids(mocker):
    return mocker.patch("services.notion.notion_db.NotionDB._save_sync_ids")


@pytest.mark.asyncio
async def test_add_item(notion_db, item, item_data):
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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
