import logging
from datetime import datetime
from sqlalchemy.orm import Session as DBSession

from src.schemas.manual_session import SessionStartRequest
from src.schemas.presence_event import PresenceEvent as PresenceEventSchema
from src.schemas.event_types import EventType, TriggerSource
from src.schemas.identity import Role
from src.repositories.presence_event_repo import PresenceEventRepository
from src.services.presence_engine import PresenceEngine
from src.services.session_manager import SessionManager

logger = logging.getLogger(__name__)


class ManualSessionService:
    """
    Coordinates session lifecycle events initiated via the REST API.
    Converts manual REST requests into PresenceEvents and dispatches them
    through the identical presence and session logic pipelines as barcode scanner scans.
    """
    def __init__(self, presence_engine: PresenceEngine, session_manager: SessionManager):
        self.presence_engine = presence_engine
        self.session_manager = session_manager

    def start_session(self, request: SessionStartRequest, db: DBSession) -> dict:
        active = self.session_manager.get_active_session(db)
        if active:
            raise ValueError(f"Session already active: {active.subject} by {active.faculty_name}")

        event = PresenceEventSchema(
            event_type=EventType.FACULTY_ENTER,
            actor_id=request.faculty_id,
            actor_role=Role.FACULTY,
            classroom_id=request.room,
            trigger_source=TriggerSource.MANUAL,
            metadata={"subject": request.subject},
            timestamp=datetime.utcnow()
        )

        # 1. Append Event to immutable ledger
        PresenceEventRepository(db).append(event)

        # 2. Process state change in PresenceEngine
        self.presence_engine.process_event(event, db)

        # 3. Trigger SessionManager logic to create DB record
        result = self.session_manager.handle_event(event, db)
        if not result or result.get("status") != "session_started":
            raise RuntimeError("Failed to start session via SessionManager")
            
        return result

    def end_session(self, db: DBSession) -> dict:
        active = self.session_manager.get_active_session(db)
        if not active:
            raise ValueError("No active session")

        session_id = active.id
        faculty_id = active.faculty_id or "FAC-01"

        event = PresenceEventSchema(
            event_type=EventType.FACULTY_EXIT,
            actor_id=faculty_id,
            actor_role=Role.FACULTY,
            classroom_id=active.room or "Room-1",
            trigger_source=TriggerSource.MANUAL,
            timestamp=datetime.utcnow()
        )

        # 1. Append Event to ledger
        PresenceEventRepository(db).append(event)

        # 2. Process state change in PresenceEngine
        self.presence_engine.process_event(event, db)

        # 3. Trigger SessionManager logic to close DB record
        result = self.session_manager.handle_event(event, db)
        if not result or result.get("status") != "session_ended":
            raise RuntimeError("Failed to end session via SessionManager")

        # 4. Trigger Batch Attendance Derivation
        from src.services.attendance_derivation_service import AttendanceDerivationService
        derivation_svc = AttendanceDerivationService()
        derivation_svc.derive_session_attendance(session_id, db)

        return result
