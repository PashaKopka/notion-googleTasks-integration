import asyncio

import pytest

from config import REDIS_URL
from models.models import SyncingService, User
from redis_client import RedisClient
from tests.utils import google_tasks_data, notion_data
from utils.db_utils import generate_access_token

redis_client = RedisClient(REDIS_URL)
fake_task = asyncio.Future()
fake_task.set_result(None)


@pytest.fixture
async def user(db):
    user = User(email="test_sync_route@test.com", password="password")
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
async def syncing_service_not_ready(db, user):
    syncing_service = SyncingService(
        user_id=user.id,
    )
    yield await syncing_service.save(db)
    await syncing_service.delete(db)


@pytest.fixture
def token(user):
    token, _ = generate_access_token(user)
    return f"Bearer {token}"


@pytest.fixture
def auth_header(token):
    return {"Authorization": token}


@pytest.fixture
def mock_start_sync_notion_google_tasks(mocker):
    future = asyncio.Future()
    future.set_result(None)

    method = mocker.patch("routes.sync.start_sync_notion_google_tasks")
    method.return_value = future
    return method


@pytest.fixture
def mock_asyncio_all_tasks(mocker, syncing_service):
    redis_client.set(syncing_service.id, str(id(fake_task)))
    method = mocker.patch("asyncio.all_tasks")
    method.return_value = [fake_task]
    return method


def test_start_sync_no_syncing_service(client, auth_header):
    result = client.post(
        "/sync/start_sync",
        headers=auth_header,
    )
    assert result.status_code == 400
    assert result.json() == {"detail": "Not all services are connected"}


def test_start_sync_syncing_service_not_ready(
    client,
    auth_header,
    syncing_service_not_ready,
):
    result = client.post(
        "/sync/start_sync",
        headers=auth_header,
    )
    assert result.status_code == 400
    assert result.json() == {"detail": "Not all services are connected"}


async def test_start_sync(
    client,
    auth_header,
    syncing_service,
    mock_start_sync_notion_google_tasks,
    db,
):
    result = client.post(
        "/sync/start_sync",
        headers=auth_header,
    )
    assert result.status_code == 201

    mock_start_sync_notion_google_tasks.assert_called_once()

    service = await SyncingService.get_service_by_user_id(syncing_service.user_id, db)
    assert service.is_active

    task_id = redis_client.get(service.id)
    assert task_id


def test_stop_sync_no_syncing_service(client, auth_header):
    result = client.post(
        "/sync/stop_sync",
        headers=auth_header,
    )
    assert result.status_code == 400
    assert result.json() == {"detail": "Syncing service not found"}


async def test_stop_sync_no_task(client, auth_header, syncing_service, db):
    result = client.post(
        "/sync/stop_sync",
        headers=auth_header,
    )
    assert result.status_code == 204

    service = await SyncingService.get_service_by_user_id(syncing_service.user_id, db)
    assert not service.is_active

    task_id = redis_client.get(service.id)
    assert not task_id


async def test_stop_sync(
    client, auth_header, syncing_service, mock_asyncio_all_tasks, db
):
    result = client.post(
        "/sync/stop_sync",
        headers=auth_header,
    )
    assert result.status_code == 204

    service = await SyncingService.get_service_by_user_id(syncing_service.user_id, db)
    assert not service.is_active

    task_id = redis_client.get(service.id)
    assert not task_id
