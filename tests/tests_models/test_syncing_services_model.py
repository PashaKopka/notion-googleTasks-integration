import pytest

from models.models import SyncingServices, User


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


ready_to_start_params = [
    {"notion_data": {}, "google_tasks_data": {}, "is_ready": False},
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
    syncing_service = SyncingServices(
        user_id=user.id,
        service_google_tasks_data=request.param["google_tasks_data"],
        service_notion_data=request.param["notion_data"],
    )
    yield await syncing_service.save(db), request.param["is_ready"]
    await syncing_service.delete(db)


@pytest.fixture
async def syncing_service_ready(db, user):
    syncing_service = SyncingServices(
        user_id=user.id,
        service_google_tasks_data={"tasks_list_id": "tasks_list_id"},
        service_notion_data={
            "duplicated_template_id": "duplicated_template_id",
            "title_prop_name": "title_prop_name",
        },
        ready=True,
    )
    yield await syncing_service.save(db)
    await syncing_service.delete(db)


async def test_ready_to_start_sync(syncing_service_ready_to_start_sync, db):
    syncing_service, is_ready = syncing_service_ready_to_start_sync
    assert await syncing_service.ready_to_start_sync(db) == is_ready


async def test_get_service_by_user_id(syncing_service, user, db):
    service = await SyncingServices.get_service_by_user_id(user.id, db)
    assert service is not None
    assert service.id == syncing_service.id
    assert service.user_id == user.id


async def test_get_ready_services(syncing_service_ready, db):
    services = await SyncingServices.get_ready_services(db)
    assert len(services) == 1
    assert services[0].id == syncing_service_ready.id
    assert services[0].ready


async def test_update(syncing_service, db):
    new_google_tasks_data = {"new": "data"}
    new_notion_data = {"new": "data"}

    updated_service = await SyncingServices.update(
        syncing_service.user_id,
        {
            "service_google_tasks_data": new_google_tasks_data,
            "service_notion_data": new_notion_data,
        },
        db,
    )

    assert updated_service.id == syncing_service.id
    assert updated_service.service_google_tasks_data == new_google_tasks_data
    assert updated_service.service_notion_data == new_notion_data
