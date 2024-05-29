from sqlalchemy.ext.asyncio import AsyncSession

from models.models import GoogleTasksData, NotionData, SyncingService


async def notion_data(
    syncing_service: SyncingService,
    db: AsyncSession,
    values: dict = None,
):
    if values:
        notion_data = NotionData(**values)
    else:
        notion_data = NotionData(
            access_token="access_token",
            duplicated_template_id="duplicated_template_id",
            title_prop_name="title_prop_name",
            syncing_service_id=syncing_service.id,
            data={
                "duplicated_template_id": "duplicated_template_id",
                "title_prop_name": "title_prop_name",
            },
        )
    await notion_data.save(db)
    return notion_data


async def google_tasks_data(
    syncing_service: SyncingService,
    db: AsyncSession,
    values: dict = None,
):
    if values:
        google_tasks_data = GoogleTasksData(**values)
    else:
        google_tasks_data = GoogleTasksData(
            token="token",
            refresh_token="refresh_token",
            token_uri="token_uri",
            client_id="client_id",
            client_secret="client_secret",
            tasks_list_id="tasks_list_id",
            data={
                "token": "token",
                "refresh_token": "refresh",
                "token_uri": "token_uri",
                "client_id": "client_id",
                "client_secret": "client",
                "tasks_list_id": "tasks_list_id",
            },
            syncing_service_id=syncing_service.id,
        )
    await google_tasks_data.save(db)
    return google_tasks_data
