"""
Session repository — database access for faculty class sessions.
"""
from datetime import datetime

from sqlalchemy.orm import Session as DBSession

from src.models.session import Session as ClassSession


class SessionRepository:
    def __init__(self, db: DBSession):
        self.db = db

    def get_active(self) -> ClassSession | None:
        """Get the currently active session (at most one at a time for pilot)."""
        return (
            self.db.query(ClassSession)
            .filter(ClassSession.status == "active")
            .first()
        )

    def get_by_id(self, session_id: int) -> ClassSession | None:
        return self.db.query(ClassSession).filter(ClassSession.id == session_id).first()

    def start_session(
        self, faculty: str, subject: str, slot: str, room: str = "Room-1"
    ) -> ClassSession:
        session = ClassSession(
            faculty_name=faculty,
            subject=subject,
            slot=slot,
            room=room,
            started_at=datetime.now().isoformat(),
            status="active",
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def end_session(self, session_id: int):
        self.db.query(ClassSession).filter(ClassSession.id == session_id).update(
            {"ended_at": datetime.now().isoformat(), "status": "completed"}
        )
        self.db.commit()

    def get_today_sessions(self) -> list[ClassSession]:
        today = datetime.now().strftime("%Y-%m-%d")
        return (
            self.db.query(ClassSession)
            .filter(ClassSession.started_at.like(f"{today}%"))
            .all()
        )
