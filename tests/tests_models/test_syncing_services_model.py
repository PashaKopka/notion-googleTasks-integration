import pytest

from models.models import SyncingService, User
from tests.utils import google_tasks_data, notion_data


@pytest.fixture
async def user(db):
    user = User(email="test_syncing_service_model@test.com", password="password")
    yield await user.save(db)
    await user.delete(db)


@pytest.fixture
async def syncing_service(db, user):
    syncing_service = SyncingService(
        user_id=user.id,
    )
    service = await syncing_service.save(db)

    notion = await notion_data(syncing_service, db)
    google_tasks = await google_tasks_data(syncing_service, db)
    yield service

    await notion.delete(db)
    await google_tasks.delete(db)
    await syncing_service.delete(db)


ready_to_start_params = [
    # {"notion_data": {}, "google_tasks_data": {}, "is_ready": False},
    {
        "notion_data": {"some": "data"},
        "google_tasks_data": {"some": "data"},
        "is_ready": False,
    },
    {
        "notion_data": {"duplicated_template_id": "data", "title_prop_name": "data"},
        "google_tasks_data": {"some": "data"},
        "is_ready": False,
    },
    {
        "notion_data": {"title_prop_name": "data"},
        "google_tasks_data": {"tasks_list_id": "data"},
        "is_ready": False,
    },
    {
        "notion_data": {"duplicated_template_id": "data"},
        "google_tasks_data": {"tasks_list_id": "data"},
        "is_ready": False,
    },
    {
        "notion_data": {"duplicated_template_id": "data", "title_prop_name": "data"},
        "google_tasks_data": {"tasks_list_id": "data"},
        "is_ready": True,
    },
]


@pytest.fixture(params=ready_to_start_params)
async def syncing_service_ready_to_start_sync(db, user, request):
    syncing_service = SyncingService(
        user_id=user.id,
        is_active=True,
    )
    service = await syncing_service.save(db)

    notion_values = {
        "duplicated_template_id": request.param["notion_data"].get(
            "duplicated_template_id"
        )
        or "",
        "title_prop_name": request.param["notion_data"].get("title_prop_name") or "",
        "access_token": "access_token",
        "syncing_service_id": service.id,
        "data": request.param["notion_data"],
    }
    google_values = {
        "tasks_list_id": request.param["google_tasks_data"].get("tasks_list_id") or "",
        "token": "token",
        "refresh_token": "refresh_token",
        "token_uri": "token_uri",
        "client_id": "client_id",
        "client_secret": "client_secret",
        "syncing_service_id": service.id,
        "data": request.param["google_tasks_data"],
    }

    notion = await notion_data(syncing_service, db, notion_values)
    google_tasks = await google_tasks_data(syncing_service, db, google_values)

    await db.refresh(service)
    yield service, request.param["is_ready"]

    await notion.delete(db)
    await google_tasks.delete(db)
    await syncing_service.delete(db)


@pytest.fixture
async def syncing_service_ready(db, user):
    syncing_service = SyncingService(
        user_id=user.id,
        ready=True,
    )
    yield await syncing_service.save(db)
    await syncing_service.delete(db)


async def test_ready_to_start_sync(syncing_service_ready_to_start_sync, db):
    syncing_service, is_ready = syncing_service_ready_to_start_sync
    assert await syncing_service.ready_to_start_sync(db) == is_ready


async def test_get_service_by_user_id(syncing_service, user, db):
    service = await SyncingService.get_service_by_user_id(user.id, db)
    assert service is not None
    assert service.id == syncing_service.id
    assert service.user_id == user.id


async def test_get_ready_services(syncing_service_ready, db):
    services = await SyncingService.get_ready_services(db)
    assert len(services) == 1
    assert services[0].id == syncing_service_ready.id
    assert services[0].ready


async def test_update(syncing_service, db):
    new_google_tasks_data = {"new": "data"}
    new_notion_data = {"new": "data"}

    updated_service = await SyncingService.update(
        syncing_service.user_id,
        {"ready": True, "is_active": True},
        db,
    )

    assert updated_service.id == syncing_service.id
    assert updated_service.ready is True
    assert updated_service.is_active is True
