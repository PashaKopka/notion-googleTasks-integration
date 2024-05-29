from contextlib import contextmanager

import pytest
from pydantic import ValidationError

from models.models import GoogleTasksData, NotionData, SyncingService, User
from schemas.user_data import UserData
from tests.utils import google_tasks_data, notion_data
from utils.crypt_utils import generate_access_token


@contextmanager
def not_raises(ExpectedException):
    try:
        yield

    except ExpectedException as error:
        raise AssertionError(f"Raised exception {error} when it should not!")

    except Exception as error:
        raise AssertionError(f"An unexpected exception {error} raised.")


@pytest.fixture
async def user(db):
    user = User(email="test_user_route@test.com", password="password")
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


@pytest.fixture
def token(user):
    token, _ = generate_access_token(user)
    return f"Bearer {token}"


@pytest.fixture
def auth_header(token):
    return {"Authorization": token}


def test_register_no_username(client):
    response = client.post(
        "/register",
        data={
            "username": "",
            "password": "",
        },
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Username and password are required"}


def test_register_no_password(client):
    response = client.post(
        "/register",
        data={
            "username": "test_user_route@test.com",
            "password": "",
        },
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Username and password are required"}


async def test_register(client, db):
    response = client.post(
        "/register",
        data={
            "username": "test_user_route@test.com",
            "password": "test",
        },
    )
    assert response.status_code == 200
    response_json = response.json()
    assert "access_token" in response_json
    assert response_json["token_type"] == "bearer"
    assert "expired_in" in response_json

    user = await User.get_by_email("test_user_route@test.com", db)
    assert user is not None
    assert user.email == "test_user_route@test.com"
    assert user.password != "test"

    await user.delete(db)


def test_token_no_user(client):
    response = client.post(
        "/token",
        data={
            "username": "test_user_route@test.com",
            "password": "password",
        },
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Incorrect username or password"}


def test_token_wrong_password(client, user):
    response = client.post(
        "/token",
        data={
            "username": "test_user_route@test.com",
            "password": "wrong_password",
        },
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Incorrect username or password"}


def test_token(client, user):
    response = client.post(
        "/token",
        data={
            "username": "test_user_route@test.com",
            "password": "password",
        },
    )
    assert response.status_code == 200
    response_json = response.json()
    assert "access_token" in response_json
    assert response_json["token_type"] == "bearer"
    assert "expired_in" in response_json


def test_get_user_data_no_syncing_service(client, auth_header):
    response = client.get("/user_data", headers=auth_header)
    assert response.status_code == 400
    assert response.json() == {"detail": "Syncing service not found"}


def test_get_user_data(client, auth_header, syncing_service):
    response = client.get("/user_data", headers=auth_header)
    assert response.status_code == 200

    with not_raises(ValidationError):
        UserData(**response.json())


def test_save_user_data_no_syncing_service(client, auth_header):
    response = client.post(
        "/user_data",
        json={
            "google_tasks_list_id": "new_tasks_list_id",
            "notion_list_id": "new_notion_list_id",
            "notion_title_prop_name": "new_title_prop_name",
        },
        headers=auth_header,
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Syncing service not found"}


async def test_save_user_data(client, auth_header, syncing_service, db):
    response = client.post(
        "/user_data",
        headers=auth_header,
        json={
            "google_tasks_list_id": "new_tasks_list_id",
            "notion_list_id": "new_notion_list_id",
            "notion_title_prop_name": "new_title_prop_name",
        },
    )
    assert response.status_code == 201
    with not_raises(ValidationError):
        UserData(**response.json())

    google_tasks = await GoogleTasksData.get_by_syncing_service_id(
        syncing_service.id, db
    )
    notion = await NotionData.get_by_syncing_service_id(syncing_service.id, db)
    assert google_tasks.tasks_list_id == "new_tasks_list_id"
    assert notion.duplicated_template_id == "new_notion_list_id"
    assert notion.title_prop_name == "new_title_prop_name"
