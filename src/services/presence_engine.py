import logging
from sqlalchemy.orm import Session as DBSession

from src.services.presence_state_machine import PresenceStateMachine
from src.repositories.presence_state_repo import PresenceStateRepository
from src.schemas.presence_event import PresenceEvent
from src.schemas.identity import Role

logger = logging.getLogger(__name__)


class PresenceEngine:
    """
    Public orchestration service for classroom physical presence state.
    Responsible for receiving PresenceEvents, executing state transitions,
    and persisting updates to runtime presence database tables.
    """

    def __init__(self, state_machine: PresenceStateMachine = None):
        self.state_machine = state_machine or PresenceStateMachine()
        # In-memory store for tracking faculty presence states
        # (Prevents foreign key violations since student_presence_states is student-only)
        self.faculty_states = {}

    def process_event(self, event: PresenceEvent, db: DBSession) -> dict:
        """
        Orchestrates transition changes based on resolved presence events.
        Persists student updates to the database (without committing).
        """
        # 1. Process Student scans
        if event.actor_role == Role.STUDENT:
            repo = PresenceStateRepository(db)
            record = repo.get_or_create(event.actor_id)

            # Extract current state
            current_state = record.presence_state
            current_health = record.presence_health
            inside_since = record.inside_since
            accumulated = record.accumulated_seconds

            # Execute transition logic
            new_state, new_health, new_since, new_accumulated = self.state_machine.transition(
                current_state,
                current_health,
                inside_since,
                accumulated,
                event.event_type,
                event.timestamp
            )

            # Map parameters back to record
            record.presence_state = new_state
            record.presence_health = new_health
            record.inside_since = new_since
            record.accumulated_seconds = new_accumulated
            record.last_updated = event.timestamp

            # Register with session queue (commits left to engine boundaries)
            db.add(record)

            return {
                "actor_id": record.student_id,
                "role": "STUDENT",
                "presence_state": record.presence_state,
                "presence_health": record.presence_health,
                "inside_since": record.inside_since,
                "accumulated_seconds": record.accumulated_seconds
            }

        # 2. Process Faculty scans
        elif event.actor_role == Role.FACULTY:
            faculty_data = self.faculty_states.setdefault(event.actor_id, {
                "presence_state": "OUTSIDE",
                "presence_health": "NORMAL",
                "inside_since": None,
                "accumulated_seconds": 0
            })

            # Execute transition logic in-memory
            new_state, new_health, new_since, new_accumulated = self.state_machine.transition(
                faculty_data["presence_state"],
                faculty_data["presence_health"],
                faculty_data["inside_since"],
                faculty_data["accumulated_seconds"],
                event.event_type,
                event.timestamp
            )

            # Map parameters back to in-memory store
            faculty_data["presence_state"] = new_state
            faculty_data["presence_health"] = new_health
            faculty_data["inside_since"] = new_since
            faculty_data["accumulated_seconds"] = new_accumulated

            return {
                "actor_id": event.actor_id,
                "role": "FACULTY",
                "presence_state": faculty_data["presence_state"],
                "presence_health": faculty_data["presence_health"],
                "inside_since": faculty_data["inside_since"],
                "accumulated_seconds": faculty_data["accumulated_seconds"]
            }

        raise ValueError(f"Unsupported actor role for presence state: {event.actor_role}")
