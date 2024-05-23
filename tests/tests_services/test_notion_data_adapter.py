import datetime

import pytest

from services.notion.notion_db import NotionDBDataAdapter as Adapter
from services.service import Item

DATE = datetime.datetime(2021, 10, 10, 10, 10, 10, 10)
TITLE_PROP_NAME = "Name"
DATABASE_ID = "database_id"


@pytest.fixture
def data_adapter():
    return Adapter(
        title_prop_name=TITLE_PROP_NAME,
        database_id=DATABASE_ID,
    )


@pytest.fixture
def item():
    return Item(
        name="name",
        status=True,
        google_task_id="google_task_id",
        notion_id="notion_id",
        updated_at=DATE,
    )


def test_get_updated_at(data_adapter):
    result = data_adapter._get_updated_at(DATE.isoformat())
    assert result == DATE


def test_get_checkbox_status(data_adapter):
    data_true = {"properties": {"Checkbox": {"checkbox": True}}}
    data_false = {"properties": {"Checkbox": {"checkbox": False}}}

    assert data_adapter._get_checkbox_status(data_true) is True
    assert data_adapter._get_checkbox_status(data_false) is False


def test_get_title(data_adapter):
    data = {
        "properties": {
            TITLE_PROP_NAME: {
                "title": [{"plain_text": "name"}],
            },
        },
    }

    result = data_adapter._get_title(data)
    assert result == "name"


def test_item_to_dict(data_adapter, item):
    result = data_adapter.item_to_dict(item)
    assert result == {
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


def test_dict_to_item(data_adapter, item):
    data = {
        "object": "page",
        "id": item.notion_id,
        "parent": {"type": "database_id", "database_id": DATABASE_ID},
        "last_edited_time": DATE.isoformat(),
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
    result = data_adapter.dict_to_item(data)
    assert result == item


def test_items_to_dicts(data_adapter, item):
    result = data_adapter.items_to_dicts([item])
    assert result == [
        {
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
    ]


def test_dicts_to_items(data_adapter, item):
    data = [
        {
            "object": "page",
            "id": item.notion_id,
            "parent": {"type": "database_id", "database_id": DATABASE_ID},
            "last_edited_time": DATE.isoformat(),
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
    ]
    result = data_adapter.dicts_to_items(data)
    assert result == [item]
