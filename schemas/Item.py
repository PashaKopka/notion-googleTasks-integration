import datetime
from dataclasses import dataclass, field


@dataclass(slots=True)
class Item:
    name: str
    status: bool
    updated_at: datetime = field(compare=False)

    # services
    notion_id: str = field(default="", compare=False)
    google_task_id: str = field(default="", compare=False)
