"""Pydantic schemas for Session API."""
from pydantic import BaseModel


class SessionStart(BaseModel):
    faculty_name: str
    subject: str
    room: str = "Room-1"


class SessionResponse(BaseModel):
    id: int
    faculty_name: str
    subject: str
    slot: str
    room: str
    started_at: str
    ended_at: str | None
    status: str

    model_config = {"from_attributes": True}
