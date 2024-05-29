from functools import wraps
from types import UnionType
from typing import Callable, get_type_hints

from sqlalchemy.ext.asyncio import AsyncSession

from models.models import GoogleTasksData, NotionData, SyncingService
from schemas.services_auth_data import GoogleAuthData, NotionAuthData


def get_dataclass_type(args):
    for arg in args:
        if hasattr(arg, "__dataclass_fields__"):
            return arg
    return None


def argument_to_dataclass(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        type_hints = get_type_hints(func)

        for arg_name, arg_value in kwargs.items():
            if arg_name in type_hints:
                arg_type = type_hints[arg_name]

                if isinstance(arg_type, UnionType):
                    arg_type = get_dataclass_type(arg_type.__args__)

                if arg_value is not None and hasattr(arg_type, "__dataclass_fields__"):
                    kwargs[arg_name] = arg_type(**arg_value, data=arg_value)

        return func(*args, **kwargs)

    return wrapper


@argument_to_dataclass
async def create_or_update_syncing_service(
    user_id: str,
    db: AsyncSession,
    google_tasks_data: GoogleAuthData | None = None,
    notion_data: NotionAuthData | None = None,
) -> SyncingService:
    service = await SyncingService.get_service_by_user_id(user_id, db)
    if not service:
        service = SyncingService(user_id=user_id)
        await service.save(db)

    if google_tasks_data:
        google_tasks_data = GoogleTasksData.create_from_auth_data(
            google_tasks_data,
            syncing_service_id=service.id,
        )
        await google_tasks_data.save(db)

    if notion_data:
        notion_data = NotionData.create_from_auth_data(
            notion_data,
            syncing_service_id=service.id,
        )
        await notion_data.save(db)

    return service
