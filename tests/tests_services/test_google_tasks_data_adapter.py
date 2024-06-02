import datetime

import pytest

from services.google_tasks.google_tasks import GTasksDataAdapter as Adapter
from schemas.Item import Item


@pytest.fixture
def google_tasks_data_adapter():
    return Adapter()


@pytest.fixture
def item():
    return Item(
        name="name",
        status=True,
        google_task_id="google_task_id",
        notion_id="notion_id",
        updated_at=datetime.datetime(2021, 10, 10, 10, 10, 10, 10),
    )


def test_get_updated_at(google_tasks_data_adapter):
    time = datetime.datetime(2021, 10, 10, 10, 10, 10, 10)
    result = google_tasks_data_adapter._get_updated_at(time.isoformat())
    assert result == time


def test_convert_status_to_bool(google_tasks_data_adapter):
    assert google_tasks_data_adapter.convert_status_to_bool("completed") is True
    assert google_tasks_data_adapter.convert_status_to_bool("needsAction") is False


def test_convert_status_to_text(google_tasks_data_adapter):
    assert google_tasks_data_adapter.convert_status_to_text(True) == "completed"
    assert google_tasks_data_adapter.convert_status_to_text(False) == "needsAction"


def test_item_to_dict(google_tasks_data_adapter, item):
    result = google_tasks_data_adapter.item_to_dict(item)
    assert result == {
        "kind": "tasks#task",
        "id": item.google_task_id,
        "title": item.name,
        "status": "completed",
    }


def test_dict_to_item(google_tasks_data_adapter, item):
    data = {
        "id": item.google_task_id,
        "title": item.name,
        "status": "completed",
        "updated": item.updated_at.isoformat(),
    }
    result = google_tasks_data_adapter.dict_to_item(data)
    assert result == item


def test_items_to_dicts(google_tasks_data_adapter, item):
    result = google_tasks_data_adapter.items_to_dicts([item])
    assert result == [
        {
            "kind": "tasks#task",
            "id": item.google_task_id,
            "title": item.name,
            "status": "completed",
        }
    ]


def test_dicts_to_items(google_tasks_data_adapter, item):
    data = [
        {
            "id": item.google_task_id,
            "title": item.name,
            "status": "completed",
            "updated": item.updated_at.isoformat(),
        }
    ]
    result = google_tasks_data_adapter.dicts_to_items(data)
    assert result == [item]
