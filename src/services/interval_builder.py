import logging
from src.schemas.attendance_policy import PresenceInterval
from src.schemas.event_types import EventType

logger = logging.getLogger(__name__)


class IntervalBuilder:
    """
    Pure domain service to reconstruct classroom presence intervals from presence events.
    Operates in-memory with zero side effects or external dependencies.
    """

    @staticmethod
    def build_intervals(events: list) -> list[PresenceInterval]:
        """
        Processes a list of PresenceEvents for one student, sorts them, and reconstructs
        continuous presence intervals. Handles edge cases deterministically:
        - Out-of-order events: sorted by timestamp ascending first.
        - Duplicate ENTER: ignores subsequent entries if already inside.
        - Duplicate EXIT: ignores subsequent exits if already outside.
        - EXIT without ENTER: ignored.
        - ENTER without EXIT (Open interval): exit_time remains None.
        """
        if not events:
            return []

        # 1. Sort events chronologically to resolve out-of-order sequences
        # Works on both Pydantic schemas and ORM models having a .timestamp attribute
        sorted_events = sorted(events, key=lambda x: x.timestamp)

        intervals = []
        inside = False
        current_interval = None

        for event in sorted_events:
            # Map event type strings or enums to check type
            evt_type = event.event_type
            if not isinstance(evt_type, str):
                evt_type = evt_type.value

            if evt_type in ("STUDENT_ENTER", "FACULTY_ENTER"):
                if not inside:
                    current_interval = PresenceInterval(enter_time=event.timestamp)
                    inside = True
                else:
                    # Duplicate enter: ignore to preserve initial entry timestamp
                    logger.debug(f"Duplicate ENTER event ignored for actor {event.actor_id} at {event.timestamp}")

            elif evt_type in ("STUDENT_EXIT", "FACULTY_EXIT"):
                if inside:
                    current_interval.exit_time = event.timestamp
                    intervals.append(current_interval)
                    current_interval = None
                    inside = False
                else:
                    # EXIT without ENTER / Duplicate EXIT: ignore
                    logger.debug(f"EXIT without matching ENTER ignored for actor {event.actor_id} at {event.timestamp}")

        # Handle open intervals (ENTER without EXIT at the end of the sequence)
        if inside and current_interval is not None:
            intervals.append(current_interval)

        return intervals
