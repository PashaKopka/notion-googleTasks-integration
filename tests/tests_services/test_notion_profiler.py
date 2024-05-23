import pytest

from services.notion.notion_profiler import NotionProfiler

pytest_plugins = ("pytest_asyncio",)

TOKEN = "token"
SEARCH_URL = "https://api.notion.com/v1/search"
TOKEN_URI = "https://oauth2.googleapis.com/token"
CLIENT_ID = "client_id"
CLIENT_SECRET = "client_secret"
REFRESH_TOKEN = "refresh_token"
TASKS_LIST_URL = "https://tasks.googleapis.com/tasks/v1/users/@me/lists/"


@pytest.fixture
def profiler():
    return NotionProfiler(token=TOKEN)


def test_get_lists(profiler, requests_mock):
    requests_mock.post(
        SEARCH_URL,
        json={
            "results": [
                {
                    "id": "list_id",
                    "title": [{"plain_text": "title"}],
                }
            ]
        },
    )

    result = profiler.get_lists()

    assert result == {"list_id": {"title": "title", "id": "list_id"}}
