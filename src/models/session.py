"""
Session model — faculty-initiated class sessions.
A session represents one period of one subject by one faculty member.
"""
from sqlalchemy import Column, Integer, Text, ForeignKey
from src.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    faculty_name = Column(Text, nullable=False)
    faculty_id = Column(Text, ForeignKey("faculty.id"), nullable=True)
    subject = Column(Text, nullable=False)
    slot = Column(Text, nullable=False)  # "Hour 1", "Hour 2", etc.
    room = Column(Text, default="Room-1")
    started_at = Column(Text, nullable=False)
    ended_at = Column(Text)  # NULL = still active
    status = Column(Text, default="active")  # active | completed

    def __repr__(self):
        return f"<Session {self.id}: {self.subject} by {self.faculty_name}>"

