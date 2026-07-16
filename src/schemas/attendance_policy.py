from datetime import datetime
from pydantic import BaseModel, Field


class PresenceInterval(BaseModel):
    enter_time: datetime
    exit_time: datetime | None = None


class ParticipationMetrics(BaseModel):
    participation_seconds: int
    participation_percentage: float
    late_minutes: int
    early_departure_minutes: int
    entries: int
    exits: int
    entered_before_session: bool
    inside_at_session_end: bool


class InstitutionPolicy(BaseModel):
    policy_id: str
    version: str
    effective_from: datetime
    effective_to: datetime | None = None
    minimum_attendance_percentage: float = 75.0
    late_grace_minutes: int = 10
    early_exit_grace_minutes: int = 10
    regularization_threshold: float = 50.0
    allow_multiple_entries: bool = True
    count_breaks: bool = True
    maximum_break_minutes: int = 15
    medical_override_enabled: bool = True


class PolicyContext(BaseModel):
    student_id: str
    session_id: int
    session_start: datetime
    session_end: datetime
    metrics: ParticipationMetrics
    policy: InstitutionPolicy


class AttendanceDecision(BaseModel):
    status: str  # PRESENT | ABSENT | REGULARIZATION
    present: bool
    regularization_required: bool
    reason: str
    policy_id: str
    policy_version: str
    computed_at: datetime = Field(default_factory=datetime.utcnow)


class AttendanceRecord(BaseModel):
    student_id: str
    session_id: int
    participation_seconds: int
    participation_percentage: float
    status: str
    regularization_required: bool
    late_minutes: int
    early_departure_minutes: int
    policy_version: str
    computed_at: datetime = Field(default_factory=datetime.utcnow)
