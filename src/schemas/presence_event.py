from datetime import datetime
from pydantic import BaseModel, ConfigDict
from src.schemas.event_types import EventType, TriggerSource
from src.schemas.identity import Role


class PresenceEvent(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    event_id: int | None = None
    event_version: str = "1.0"
    event_type: EventType
    actor_id: str
    actor_role: Role
    classroom_id: str = "Room-1"
    trigger_source: TriggerSource = TriggerSource.SCANNER
    metadata: dict | None = None
    timestamp: datetime
