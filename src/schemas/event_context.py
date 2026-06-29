from datetime import datetime
from pydantic import BaseModel, ConfigDict
from src.schemas.identity import AuthenticationResult


class EventContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    auth_result: AuthenticationResult
    student_presence_state: str | None = None  # "INSIDE" | "OUTSIDE" | "STALE"
    faculty_presence_state: str | None = None  # "INSIDE" | "OUTSIDE"
    last_scan_timestamp: datetime | None = None
    current_time: datetime
