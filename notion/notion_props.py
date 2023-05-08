from abc import ABC, abstractmethod
import datetime


class AbstractNotionProperty(ABC):

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError('Name must be a string')
        self._name = value

    @property
    def value(self) -> str:
        return self._value

    @abstractmethod
    def deserialize(self) -> dict:
        raise NotImplementedError


class NotionTitle(AbstractNotionProperty):

    def __init__(self, name: str, data: dict | str) -> None:
        super().__init__()
        self._name = name
        if isinstance(data, str):
            self._value = data
        elif isinstance(data, dict):
            self._value = self._parse_text(data['title'])

    def _parse_text(self, text: list) -> str:
        return ''.join([t['plain_text'] for t in text])

    def deserialize(self) -> dict:
        return {
            self.name: {
                'type': 'title',
                'title': [{
                    'type': 'text',
                    'text': {
                        'content': self.value,
                    },
                }],
            }
        }


class NotionCheckbox(AbstractNotionProperty):

    def __init__(self, name: str, data: dict | bool) -> None:
        super().__init__()
        self._name = name
        if isinstance(data, bool):
            self._value = data
        elif isinstance(data, dict):
            self._value = data['checkbox']

    @property
    def value(self) -> bool:
        return self._value

    @value.setter
    def value(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise TypeError('Name must be a bool')
        self._checked = value

    def deserialize(self) -> dict:
        return {
            'Checkbox': {
                'type': 'checkbox',
                'checkbox': self.value
            },
        }


class NotionLastEditedTime(AbstractNotionProperty):

    def __init__(self, name: str, data: dict) -> None:
        super().__init__()
        self._name = name
        self._date = self._parse_date(data['last_edited_time'])

    def _parse_date(self, date: str) -> str:
        return datetime.datetime.fromisoformat(date)


class NotionText(AbstractNotionProperty):

    def __init__(self, name: str, data: dict | str) -> None:
        super().__init__()
        self._name = name
        if isinstance(data, str):
            self._value = data
        elif isinstance(data, dict):
            self._value = self._parse_text(data['rich_text'])

    # TODO maybe should make separate class for text props
    def _parse_text(self, text: list) -> str:
        return ''.join([t['plain_text'] for t in text])

    def deserialize(self) -> dict:
        return {
            self.name: {
                'type': 'rich_text',
                'rich_text': [{
                    'type': 'text',
                    'text': {
                        'content': self.value,
                    },
                }],
            }
        }


class NotionPropertyFabric:
    NOTION_COLUMNS = {
        'title': NotionTitle,
        'checkbox': NotionCheckbox,
        'last_edited_time': NotionLastEditedTime,
        'rich_text': NotionText
    }

    @staticmethod
    def create_notion_prop(prop_name: str, prop_data: dict):
        column_type = prop_data['type']
        return NotionPropertyFabric.NOTION_COLUMNS[column_type](prop_name, prop_data)
