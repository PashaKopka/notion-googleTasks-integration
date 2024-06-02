import asyncio
import datetime

import pytest
from aioresponses import aioresponses

from models.models import SyncedItem, SyncingService, User
from services.google_tasks.google_tasks import GTasksList
from schemas.Item import Item
from tests.utils import google_tasks_data, notion_data

pytest_plugins = ("pytest_asyncio",)

TASK_LIST_ID = "tasks_list_id"
GET_ALL_URL = f"https://tasks.googleapis.com/tasks/v1/lists/{TASK_LIST_ID}/tasks?showCompleted=true&showHidden=true"
UPDATE_URL = f"https://tasks.googleapis.com/tasks/v1/lists/{TASK_LIST_ID}/tasks/{{}}"
ADD_URL = f"https://tasks.googleapis.com/tasks/v1/lists/{TASK_LIST_ID}/tasks"
DATETIME = datetime.datetime(2021, 10, 10, 10, 10, 10, 10)
TOKEN_URI = "https://oauth2.googleapis.com/token"
CLIENT_ID = "client_id"
CLIENT_SECRET = "client_secret"
REFRESH_TOKEN = "refresh_token"


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
async def user(db):
    user = User(email="test_google_tasks@test.com", password="password")
    yield await user.save(db)
    await user.delete(db)


@pytest.fixture
async def syncing_service(db, user):
    syncing_service = SyncingService(
        user_id=user.id,
        is_active=True,
    )
    service = await syncing_service.save(db)

    notion = await notion_data(syncing_service, db)
    google_tasks = await google_tasks_data(syncing_service, db)
    yield service

    await notion.delete(db)
    await google_tasks.delete(db)
    await syncing_service.delete(db)


@pytest.fixture
def tasks_list(syncing_service, db):
    return GTasksList(
        syncing_service_id=syncing_service.id,
        client_config={
            "tasks_list_id": TASK_LIST_ID,
            "token": "token",
            "token_uri": TOKEN_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": REFRESH_TOKEN,
        },
        db=db,
    )


def test_add_task_url(tasks_list):
    assert tasks_list._add_task_url == ADD_URL


def test_update_task_url(tasks_list):
    assert tasks_list._update_task_url == UPDATE_URL


def test_get_all_tasks_url(tasks_list):
    assert tasks_list._get_all_tasks_url == GET_ALL_URL


async def test_add_item(tasks_list, item, db):
    with aioresponses() as m:
        m.post(
            ADD_URL,
            payload={
                "id": item.google_task_id,
                "title": item.name,
                "status": "completed",
            },
        )

        result = await tasks_list.add_item(item)
        assert result is None
        m.assert_called_once_with(
            ADD_URL,
            method="POST",
            headers=tasks_list._headers,
            json={
                "kind": "tasks#task",
                "id": item.google_task_id,
                "title": item.name,
                "status": "completed",
            },
        )

    db_item = await SyncedItem.get_by_sync_id(db, notion_id=item.notion_id)
    assert db_item is not None
    await db_item.delete(db)


async def test_update_item(tasks_list, item):
    with aioresponses() as m:
        m.put(
            UPDATE_URL.format(item.google_task_id),
        )

        result = await tasks_list.update_item(item)
        assert result == f"Task {item.google_task_id} updated successfully."
        m.assert_called_once_with(
            UPDATE_URL.format(item.google_task_id),
            method="PUT",
            headers=tasks_list._headers,
            data=None,
            json={
                "kind": "tasks#task",
                "id": item.google_task_id,
                "title": item.name,
                "status": "completed",
            },
        )


async def test_get_item_by_id(tasks_list, item):
    with aioresponses() as m:
        m.get(
            UPDATE_URL.format(item.google_task_id),
            payload={
                "id": "google_task_id",
                "title": "name",
                "status": "completed",
                "updated": DATETIME.isoformat(),
            },
        )

        result = await tasks_list.get_item_by_id(item.google_task_id)
        assert result == item
        m.assert_called_once_with(
            UPDATE_URL.format(item.google_task_id),
            method="GET",
            headers=tasks_list._headers,
        )


async def test_get_all_items(tasks_list, item):
    with aioresponses() as m:
        m.get(
            GET_ALL_URL,
            payload={
                "items": [
                    {
                        "id": "google_task_id",
                        "title": "name",
                        "status": "completed",
                        "updated": DATETIME.isoformat(),
                    }
                ]
            },
        )

        result = await tasks_list.get_all_items()
        assert result == [item]
        m.assert_called_once_with(
            GET_ALL_URL,
            method="GET",
            headers=tasks_list._headers,
        )


async def test_refresh_token(tasks_list):
    with aioresponses() as m:
        m.post(
            TOKEN_URI,
            body={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "refresh_token": REFRESH_TOKEN,
                "grant_type": "refresh_token",
            },
            payload={
                "access_token": "access",
                "expires_in": 123,
            },
        )

        await tasks_list._refresh_token()
        assert tasks_list._client_config["token"] == "access"
        assert tasks_list._client_config["expiry"] == 123
        assert tasks_list._headers["Authorization"] == "Bearer access"
        m.assert_called_once_with(
            TOKEN_URI,
            method="POST",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "refresh_token": REFRESH_TOKEN,
                "grant_type": "refresh_token",
            },
        )
