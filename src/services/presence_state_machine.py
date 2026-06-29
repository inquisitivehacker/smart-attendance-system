import logging
from datetime import datetime
from src.schemas.event_types import EventType

logger = logging.getLogger(__name__)


class PresenceStateMachine:
    """
    Logic engine for physical classroom occupancy state transitions.
    Tracks OUTSIDE, INSIDE, and STALE presence lifecycles.
    This component is pure and has no database or network dependencies.
    """

    def transition(
        self,
        current_state: str,
        current_health: str,
        inside_since: datetime | None,
        accumulated_seconds: int,
        event_type: EventType,
        current_time: datetime
    ) -> tuple[str, str, datetime | None, int]:
        """
        Executes transition rules and returns updated presence parameters:
        (new_state, new_health, new_inside_since, new_accumulated_seconds)
        """
        # Default state mappings
        state = current_state or "OUTSIDE"
        health = current_health or "NORMAL"
        since = inside_since
        accumulated = accumulated_seconds or 0

        # 1. Handle ENTRY events (Student or Faculty)
        if event_type in (EventType.STUDENT_ENTER, EventType.FACULTY_ENTER):
            if health == "STALE":
                # Stale reconciliation: transition to INSIDE and reset health to NORMAL.
                # Discard previous inside_since duration since it was an unrecorded exit.
                state = "INSIDE"
                health = "NORMAL"
                since = current_time
                logger.info(f"Reconciled stale presence state at entry: reset to INSIDE @ {current_time}")
            elif state == "OUTSIDE":
                state = "INSIDE"
                health = "NORMAL"
                since = current_time
                logger.info(f"State transitioned: OUTSIDE -> INSIDE @ {current_time}")

        # 2. Handle EXIT events (Student or Faculty)
        elif event_type in (EventType.STUDENT_EXIT, EventType.FACULTY_EXIT):
            if state == "INSIDE":
                state = "OUTSIDE"
                health = "NORMAL"
                if since:
                    delta = int((current_time - since).total_seconds())
                    if delta > 0:
                        accumulated += delta
                        logger.info(f"Accumulated occupancy seconds: +{delta}s (total: {accumulated}s)")
                since = None
                logger.info(f"State transitioned: INSIDE -> OUTSIDE @ {current_time}")

        return state, health, since, accumulated
