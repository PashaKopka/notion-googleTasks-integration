from pydantic import dataclasses


@dataclasses.dataclass(slots=True)
class AvailableList:
    id: str
    title: str


@dataclasses.dataclass(slots=True)
class NotionOptions:
    is_connected: bool
    chosed_list: str | None
    title_prop_name: str | None
    available_lists: dict[str, AvailableList]


@dataclasses.dataclass(slots=True)
class GoogleTasksOptions:
    is_connected: bool
    available_lists: dict[str, AvailableList]
    chosed_list: str | None


@dataclasses.dataclass(slots=True)
class Options:
    notion: NotionOptions | None
    google_tasks: GoogleTasksOptions | None


@dataclasses.dataclass(slots=True)
class UserData:
    username: str
    is_ready: bool
    is_syncing_service_ready: bool
    is_active: bool
    options: Options
