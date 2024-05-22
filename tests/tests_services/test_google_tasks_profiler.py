import pytest

from services.google_tasks.google_tasks_profiler import GTasksProfiler

pytest_plugins = ("pytest_asyncio",)


TOKEN_URI = "https://oauth2.googleapis.com/token"
CLIENT_ID = "client_id"
CLIENT_SECRET = "client_secret"
REFRESH_TOKEN = "refresh_token"
TASKS_LIST_URL = "https://tasks.googleapis.com/tasks/v1/users/@me/lists/"


@pytest.fixture
def profiler():
    return GTasksProfiler(
        client_config={
            "token": "token",
            "token_uri": TOKEN_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": REFRESH_TOKEN,
        }
    )


def test_get_lists(profiler, requests_mock):
    requests_mock.get(
        TASKS_LIST_URL,
        json={
            "items": [
                {
                    "id": "list_id",
                    "title": "title",
                }
            ]
        },
    )

    result = profiler.get_lists()

    assert result == {"list_id": {"title": "title", "id": "list_id"}}


def test_refresh_token(profiler, requests_mock):
    requests_mock.post(
        TOKEN_URI,
        json={
            "access_token": "access_token_new",
            "expires_in": 123,
        },
    )

    profiler._refresh_token()

    assert profiler._client_config["token"] == "access_token_new"
    assert profiler._client_config["expiry"] == 123
    assert profiler._headers["Authorization"] == "Bearer access_token_new"
