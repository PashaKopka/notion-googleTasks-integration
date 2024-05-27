import asyncio

import pytest

from models.models import SyncingServices, User
from routes.sync import start_sync_notion_google_tasks
from utils.crypt_utils import generate_access_token


class MyTask:
    def __init__(self):
        self.cancled = False

    def cancel(self):
        self.cancled = True

    def __await__(self):
        yield


fake_task = MyTask()


@pytest.fixture
async def user(db):
    user = User(email="test_sync_route@test.com", password="password")
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
        task_id=(str(id(fake_task))),
        is_active=True,
    )
    yield await syncing_service.save(db)
    await syncing_service.delete(db)


@pytest.fixture
async def syncing_service_not_ready(db, user):
    syncing_service = SyncingServices(
        user_id=user.id,
        service_google_tasks_data={},
        service_notion_data={},
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
def mock_asyncio_all_tasks(mocker):
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

    service = await SyncingServices.get_service_by_user_id(syncing_service.user_id, db)
    assert service.is_active
    assert service.task_id is not None


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

    service = await SyncingServices.get_service_by_user_id(syncing_service.user_id, db)
    assert not service.is_active
    assert service.task_id is None


async def test_stop_sync(
    client, auth_header, syncing_service, mock_asyncio_all_tasks, db
):
    result = client.post(
        "/sync/stop_sync",
        headers=auth_header,
    )
    assert result.status_code == 204

    assert fake_task.cancled is True

    service = await SyncingServices.get_service_by_user_id(syncing_service.user_id, db)
    assert not service.is_active
    assert service.task_id is None
