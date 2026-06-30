import logging
from sqlalchemy.orm import Session as DBSession

from src.schemas.presence_event import PresenceEvent
from src.schemas.event_types import EventType
from src.repositories.session_repo import SessionRepository
from src.repositories.faculty_repo import FacultyRepository
from src.services.timetable_service import TimetableService

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Service responsible for coordinating the academic lecture session lifecycle.
    Reacts to physical FACULTY_ENTER and FACULTY_EXIT presence events.
    Does NOT commit database transactions (managed externally).
    """

    def __init__(self):
        self.timetable = TimetableService()

    def handle_event(self, event: PresenceEvent, db: DBSession) -> dict | None:
        """
        Processes faculty presence events to start or end class sessions.
        Ignores student and invalid scans.
        """
        # SessionManager only reacts to faculty events
        if event.event_type == EventType.FACULTY_ENTER:
            session_repo = SessionRepository(db)
            active = session_repo.get_active()
            if active:
                logger.warning(f"FACULTY_ENTER received, but session is already active: {active.id}")
                return {"status": "ignored_active_exists", "session_id": active.id}

            # Lookup faculty details
            faculty_repo = FacultyRepository(db)
            faculty = faculty_repo.get_by_id(event.actor_id)
            faculty_name = faculty.name if faculty else "Unknown Faculty"

            # Determine hour slot
            slot = self.timetable.get_current_slot() or "Hour 1"

            session = session_repo.start_session(
                faculty=faculty_name,
                faculty_id=event.actor_id,
                subject="Computer Science",
                slot=slot,
                room=event.classroom_id
            )
            logger.info(f"Session successfully started: {session.id} by {faculty_name}")
            return {"status": "session_started", "session_id": session.id}

        elif event.event_type == EventType.FACULTY_EXIT:
            session_repo = SessionRepository(db)
            active = session_repo.get_active()
            if not active:
                logger.warning("FACULTY_EXIT received, but no session is currently active")
                return {"status": "ignored_no_active"}

            session_repo.end_session(active.id)
            logger.info(f"Session successfully ended: {active.id}")
            return {"status": "session_ended", "session_id": active.id}

        # Ignore student and auth failure/cooldown events
        return None

    def get_active_session(self, db: DBSession):
        """
        Exposes a read-only query to retrieve the currently active session.
        Prevents external orchestrators from coupling to the ORM directly.
        """
        return SessionRepository(db).get_active()

