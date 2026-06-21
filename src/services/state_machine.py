"""
Student state machine for Phase 2 classroom pilot.
Tracks student presence states: OFFLINE → ACTIVE → BREAK → EXITED.
Uses StudentStateRepository for database persistence.
"""
from enum import Enum
from sqlalchemy.orm import Session as DBSession

from src.repositories.student_state_repo import StudentStateRepository


class StudentState(str, Enum):
    OFFLINE = "offline"
    ACTIVE = "active"
    BREAK = "break"
    EXITED = "exited"


# Valid state transitions
TRANSITIONS: dict[StudentState, list[StudentState]] = {
    StudentState.OFFLINE: [StudentState.ACTIVE],
    StudentState.ACTIVE:  [StudentState.BREAK, StudentState.EXITED],
    StudentState.BREAK:   [StudentState.ACTIVE, StudentState.EXITED],
    StudentState.EXITED:  [StudentState.OFFLINE],  # Next day reset
}


class StudentStateMachine:
    """
    Logic wrapper around StudentStateRepository.
    Enforces valid transitions and provides bulk operations.
    """

    def __init__(self, db: DBSession):
        self.repo = StudentStateRepository(db)

    def get_state(self, student_id: str) -> StudentState:
        state_str = self.repo.get_state(student_id)
        try:
            return StudentState(state_str)
        except ValueError:
            return StudentState.OFFLINE

    def transition(self, student_id: str, target: StudentState, location: str = None) -> bool:
        """
        Attempt a state transition. Returns True if valid, False if rejected.
        """
        current = self.get_state(student_id)
        if target in TRANSITIONS.get(current, []):
            self.repo.set_state(student_id, target.value, location)
            return True
        return False

    def get_active_students(self) -> list[str]:
        """Return IDs of all students currently in ACTIVE state."""
        all_states = self.repo.get_all_states()
        return [sid for sid, state in all_states.items() if state == StudentState.ACTIVE.value]

    def bulk_transition_to_break(self):
        """Called when a break period starts."""
        all_states = self.repo.get_all_states()
        for sid, state in all_states.items():
            if state == StudentState.ACTIVE.value:
                self.repo.update_state(sid, StudentState.BREAK.value)

    def bulk_return_from_break(self, student_ids: list[str]):
        """Called when break ends — reactivate detected students."""
        for sid in student_ids:
            if self.get_state(sid) == StudentState.BREAK:
                self.repo.update_state(sid, StudentState.ACTIVE.value)

    def reset_all(self):
        """End of day reset."""
        self.repo.reset_all()

    def get_all_states(self) -> dict[str, str]:
        """Return all tracked states for dashboard display."""
        return self.repo.get_all_states()
