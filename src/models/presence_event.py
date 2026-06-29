"""
PresenceEvent model — append-only Event Store of validated occupancy/session actions.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from src.database import Base


class PresenceEvent(Base):
    __tablename__ = "presence_events"

    event_id = Column(Integer, primary_key=True, autoincrement=True)
    event_version = Column(Text, nullable=False, default="1.0")
    event_type = Column(Text, nullable=False)  # STUDENT_ENTER | STUDENT_EXIT | SESSION_START | SESSION_END
    actor_id = Column(Text, nullable=False)
    actor_role = Column(Text, nullable=False)  # STUDENT | FACULTY
    classroom_id = Column(Text, nullable=False, default="Room-1")
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    trigger_source = Column(Text, nullable=False)  # SCANNER | MANUAL
    event_metadata = Column("metadata", Text, nullable=True)  # JSON string
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)


    def __repr__(self):
        return f"<PresenceEvent {self.event_id}: {self.event_type} by {self.actor_id}>"
