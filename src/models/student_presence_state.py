"""
StudentPresenceState model — transient runtime presence and active class participation states.
"""
from datetime import datetime
from sqlalchemy import Column, Text, Integer, DateTime, ForeignKey
from src.database import Base


class StudentPresenceState(Base):
    __tablename__ = "student_presence_states"

    student_id = Column(Text, ForeignKey("students.id"), primary_key=True)
    presence_state = Column(Text, nullable=False, default="OUTSIDE")  # INSIDE | OUTSIDE
    presence_health = Column(Text, nullable=False, default="NORMAL")  # NORMAL | STALE
    session_participation = Column(Integer, nullable=False, default=0)  # 0 | 1 boolean
    inside_since = Column(DateTime, nullable=True)  # Physical entry time
    session_enter_time = Column(DateTime, nullable=True)  # Class participation start time
    accumulated_seconds = Column(Integer, nullable=False, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<StudentPresenceState {self.student_id}: {self.presence_state} ({self.presence_health})>"
