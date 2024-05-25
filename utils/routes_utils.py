from sqlalchemy.ext.asyncio import AsyncSession

from models.models import SyncingServices


async def create_or_update_syncing_service(
    user_id: str,
    google_tasks_data: dict | None,
    notion_data: dict | None,
    db: AsyncSession,
) -> SyncingServices:
    service = await SyncingServices.get_service_by_user_id(user_id, db)
    if service:
        # update the service
        update_values = {}
        if google_tasks_data:
            update_values["service_google_tasks_data"] = google_tasks_data
        if notion_data:
            update_values["service_notion_data"] = notion_data

        return await service.update(update_values)

    service = SyncingServices(
        user_id=user_id,
        service_google_tasks_data=google_tasks_data,
        service_notion_data=notion_data,
    )
    return await service.save(db)
