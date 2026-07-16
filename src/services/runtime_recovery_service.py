import time
import logging
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session as DBSession

from src.models.presence_event import PresenceEvent as PresenceEventModel
from src.services.presence_engine import PresenceEngine
from src.services.session_manager import SessionManager

logger = logging.getLogger(__name__)


class RecoveryReport:
    def __init__(self, faculty_recovered: int, faculty_inside: int, faculty_outside: int, active_sessions: int, ghost_sessions: int, duration_ms: int):
        self.faculty_recovered = faculty_recovered
        self.faculty_inside = faculty_inside
        self.faculty_outside = faculty_outside
        self.active_sessions = active_sessions
        self.ghost_sessions = ghost_sessions
        self.duration_ms = duration_ms

    def log_report(self):
        logger.info(
            f"\n"
            f"========== Runtime Recovery ==========\n"
            f"Faculty recovered : {self.faculty_recovered}\n"
            f"Faculty inside    : {self.faculty_inside}\n"
            f"Faculty outside   : {self.faculty_outside}\n"
            f"Recovered active sessions : {self.active_sessions}\n"
            f"Ghost sessions    : {self.ghost_sessions}\n"
            f"Recovery duration : {self.duration_ms} ms\n"
            f"======================================\n"
        )


class RuntimeRecoveryService:
    """
    Dedicated service for recovery and bootstrap state verification.
    Reconstructs faculty presence tracking states and identifies active ghost sessions.
    """
    def recover_runtime(self, presence_engine: PresenceEngine, session_manager: SessionManager, db: DBSession) -> RecoveryReport:
        start_time = time.time()
        
        # 1. Recover faculty presence states
        # First query distinct faculty IDs that have at least one event in the database
        faculty_ids = [
            row[0] for row in db.query(PresenceEventModel.actor_id)
            .filter(PresenceEventModel.actor_role == "FACULTY")
            .distinct()
            .all()
        ]

        recovered_inside = 0
        recovered_outside = 0

        for fac_id in faculty_ids:
            # Query the latest event chronologically for this faculty member.
            # Orders by timestamp descending and uses event_id as a deterministic tie-breaker.
            event = (
                db.query(PresenceEventModel)
                .filter(and_(
                    PresenceEventModel.actor_role == "FACULTY",
                    PresenceEventModel.actor_id == fac_id
                ))
                .order_by(desc(PresenceEventModel.timestamp), desc(PresenceEventModel.event_id))
                .first()
            )

            if event:
                state = "INSIDE" if event.event_type == "FACULTY_ENTER" else "OUTSIDE"
                presence_engine.faculty_states[fac_id] = {
                    "presence_state": state,
                    "presence_health": "NORMAL",
                    "inside_since": event.timestamp if state == "INSIDE" else None,
                    "accumulated_seconds": 0
                }
                
                if state == "INSIDE":
                    recovered_inside += 1
                else:
                    recovered_outside += 1

        # 2. Detect ghost active sessions
        active_session = session_manager.get_active_session(db)
        recovered_active_sessions = 1 if active_session else 0
        ghost_sessions = 0

        if active_session:
            ghost_sessions = 1
            logger.warning(
                f"\n"
                f"========================================================\n"
                f"WARNING: Recovered active session.\n"
                f"\n"
                f"Session ID: {active_session.id}\n"
                f"Faculty:    {active_session.faculty_name} ({active_session.faculty_id})\n"
                f"Subject:    {active_session.subject}\n"
                f"Started:    {active_session.started_at}\n"
                f"Room:       {active_session.room}\n"
                f"\n"
                f"Manual verification recommended.\n"
                f"========================================================"
            )

        duration_ms = int((time.time() - start_time) * 1000)
        report = RecoveryReport(
            faculty_recovered=len(faculty_ids),
            faculty_inside=recovered_inside,
            faculty_outside=recovered_outside,
            active_sessions=recovered_active_sessions,
            ghost_sessions=ghost_sessions,
            duration_ms=duration_ms
        )
        report.log_report()
        return report
