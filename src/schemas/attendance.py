"""Pydantic schemas for Attendance API."""
from pydantic import BaseModel


class AttendanceScanRequest(BaseModel):
    student_id: str


class AttendanceResponse(BaseModel):
    id: int
    student_id: str
    session_id: int
    status: str
    verified_at: str | None
    method: str
    created_at: str | None

    model_config = {"from_attributes": True}


class ScanResultResponse(BaseModel):
    status: str  # verified | denied | duplicate | rejected
    student_id: str | None = None
    student_name: str | None = None
    slot: str | None = None
    confidence: float | None = None
    reason: str | None = None
    session_active: bool | None = None
