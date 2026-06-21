"""
Student state repository — database access for student states.
Replaces the in-memory state tracking.
"""
from datetime import datetime
from sqlalchemy.orm import Session as DBSession

from src.models.student_state import StudentState


class StudentStateRepository:
    def __init__(self, db: DBSession):
        self.db = db

    def get_state(self, student_id: str) -> str:
        """Get the current state of a student. Defaults to OFFLINE if not found."""
        state_record = self.db.query(StudentState).filter(StudentState.student_id == student_id).first()
        if state_record:
            return state_record.state
        return "OFFLINE"

    def set_state(self, student_id: str, state: str, location: str = None) -> StudentState:
        """Upsert a student state."""
        state_record = self.db.query(StudentState).filter(StudentState.student_id == student_id).first()
        now = datetime.utcnow()
        if state_record:
            state_record.state = state
            if location is not None:
                state_record.current_location = location
            state_record.last_updated = now
        else:
            state_record = StudentState(
                student_id=student_id,
                state=state,
                current_location=location,
                last_updated=now
            )
            self.db.add(state_record)
        self.db.commit()
        return state_record

    def update_state(self, student_id: str, state: str, location: str = None) -> StudentState | None:
        """Update a student state only if they already have a record."""
        state_record = self.db.query(StudentState).filter(StudentState.student_id == student_id).first()
        if state_record:
            state_record.state = state
            if location is not None:
                state_record.current_location = location
            state_record.last_updated = datetime.utcnow()
            self.db.commit()
            return state_record
        return None

    def get_all_states(self) -> dict[str, str]:
        """Return all tracked states."""
        records = self.db.query(StudentState).all()
        return {record.student_id: record.state for record in records}

    def reset_all(self):
        """End of day reset to OFFLINE."""
        self.db.query(StudentState).update({
            "state": "OFFLINE", 
            "last_updated": datetime.utcnow()
        })
        self.db.commit()
