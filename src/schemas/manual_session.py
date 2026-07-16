from pydantic import BaseModel, Field

class SessionStartRequest(BaseModel):
    faculty_id: str
    faculty_name: str
    subject: str
    room: str = "Room-1"
    slot: str | None = None
    classroom: str | None = None
    metadata: dict | None = Field(default_factory=dict)
