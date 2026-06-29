from sqlalchemy.orm import Session as DBSession
from src.models.student_presence_state import StudentPresenceState


class PresenceStateRepository:
    def __init__(self, db: DBSession):
        self.db = db

    def get_or_create(self, student_id: str) -> StudentPresenceState:
        """Retrieve presence state record or create with default values if missing."""
        record = self.db.query(StudentPresenceState).filter(
            StudentPresenceState.student_id == student_id
        ).first()

        if not record:
            record = StudentPresenceState(
                student_id=student_id,
                presence_state="OUTSIDE",
                presence_health="NORMAL",
                session_participation=0,
                accumulated_seconds=0
            )
            self.db.add(record)
        return record
