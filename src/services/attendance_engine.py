"""
Attendance Engine — the core business logic.
Milestone 5 Refactor: Decouples Event Store and coordinates single transaction commits.
"""
from datetime import datetime
import logging

from sqlalchemy.orm import Session as DBSession

from src.config import settings
from src.repositories.session_repo import SessionRepository
from src.repositories.attendance_repo import AttendanceRepository
from src.repositories.presence_state_repo import PresenceStateRepository
from src.repositories.presence_event_repo import PresenceEventRepository
from src.services.face_service import FaceService
from src.services.identity_service import IdentityService
from src.services.event_resolver import EventResolver
from src.services.presence_engine import PresenceEngine
from src.services.timetable_service import TimetableService
from src.services.state_machine import StudentStateMachine, StudentState
from src.schemas.identity import AuthenticationStatus, Role
from src.schemas.event_context import EventContext
from src.schemas.event_types import EventType

logger = logging.getLogger(__name__)


class AttendanceEngine:
    """
    Stateful engine managing attendance verification for a classroom.
    Delegates all physical occupancy changes to PresenceEngine.
    Milestone 5: Persists resolved PresenceEvent before updating runtime state.
    
    Future Event-Driven Target Architecture (Dispatcher-based):
    AttendanceEngine
           │
           ▼
    EventDispatcher
           ├──► PresenceEventRepository (Subscribed: persists event logs)
           ├──► PresenceEngine          (Subscribed: updates occupancy status)
           ├──► SessionManager          (Subscribed: controls class sessions)
           └──► PolicyEngine            (Subscribed: derives attendance)
    """

    def __init__(
        self,
        face_service: FaceService,
        identity_service: IdentityService = None,
        event_resolver: EventResolver = None,
        presence_engine: PresenceEngine = None
    ):
        self.face_service = face_service
        self.identity_service = identity_service or IdentityService(face_service)
        self.event_resolver = event_resolver or EventResolver()
        self.presence_engine = presence_engine or PresenceEngine()
        self.timetable = TimetableService()

    def process_scan(self, scanned_id: str, frame, db: DBSession, skip_face_verification: bool = False) -> dict:
        """
        Main entry point — called by the hardware loop worker thread.
        Returns a result dict with status and details.
        """
        attendance_repo = AttendanceRepository(db)
        state_machine = StudentStateMachine(db)
        session_repo = SessionRepository(db)
        presence_repo = PresenceStateRepository(db)
        event_repo = PresenceEventRepository(db)

        # 1. Authenticate identity via IdentityService
        auth_result = self.identity_service.authenticate(scanned_id, frame, db, skip_face_verification)

        # Handle failed authentication (Early Exit - no PresenceEvent generated)
        if not auth_result.authenticated:
            db.commit()

            if auth_result.rejection_reason == AuthenticationStatus.INVALID_FORMAT:
                logger.info(f"Rejected invalid barcode: {scanned_id}")
                return {"status": "rejected", "reason": "invalid_format"}

            if auth_result.rejection_reason == AuthenticationStatus.UNKNOWN_BARCODE:
                logger.warning(f"Unknown student ID: {scanned_id}")
                return {"status": "rejected", "reason": "unknown_student", "student_id": scanned_id}

            if auth_result.rejection_reason == AuthenticationStatus.REJECTED_FACE:
                student_name = auth_result.identity.name if auth_result.identity else "Unknown"
                logger.warning(f"DENIED: {scanned_id} — face mismatch (confidence={auth_result.confidence})")
                return {
                    "status": "denied",
                    "student_id": scanned_id,
                    "student_name": student_name,
                    "reason": "face_mismatch",
                    "confidence": auth_result.confidence or 0.0,
                }

            return {"status": "rejected", "reason": auth_result.rejection_reason.value}

        # Encapsulate operations in a single SQL transaction
        try:
            # 2. Gather factual runtime context
            student_presence_state = "OUTSIDE"
            faculty_presence_state = "OUTSIDE"

            if auth_result.identity.role == Role.STUDENT:
                presence_record = presence_repo.get_or_create(scanned_id)
                student_presence_state = presence_record.presence_state
                last_scan_ts = presence_record.last_updated
            else:
                faculty_presence_state = self.presence_engine.faculty_states.get(
                    scanned_id, {}
                ).get("presence_state", "OUTSIDE")
                last_scan_ts = None

            context = EventContext(
                auth_result=auth_result,
                student_presence_state=student_presence_state,
                faculty_presence_state=faculty_presence_state,
                last_scan_timestamp=last_scan_ts,
                current_time=datetime.utcnow()
            )

            # 3. Resolve classroom event
            event = self.event_resolver.resolve_event(context)

            # 4. Handle duplicate scans (returns None from EventResolver)
            if event is None:
                db.commit()
                if last_scan_ts:
                    delta = (datetime.utcnow() - last_scan_ts).total_seconds()
                    remaining = int((settings.cooldown_seconds - delta) / 60)
                    logger.info(f"Duplicate scan blocked: {scanned_id} (wait {remaining}m)")
                    return {
                        "status": "duplicate",
                        "reason": f"wait_{remaining}m",
                        "student_id": scanned_id,
                        "student_name": auth_result.identity.name,
                    }
                return {"status": "rejected", "reason": "cooldown_duplicate"}

            # 5. Persist immutable history (Write-ahead logging)
            event_repo.append(event)

            # 6. Process presence state transition in PresenceEngine (Runtime projection)
            self.presence_engine.process_event(event, db)

            # 7. Legacy compatibility mapping triggers
            identity = auth_result.identity

            # Faculty scans: start or end academic sessions
            if event.event_type == EventType.FACULTY_ENTER:
                session = session_repo.start_session(
                    faculty=identity.name,
                    faculty_id=scanned_id,
                    subject="Computer Science",
                    slot="Hour 1"
                )
                db.commit()
                logger.info(f"Session started on Faculty Enter: {identity.name}")
                return {"status": "session_started", "session_id": session.id}

            elif event.event_type == EventType.FACULTY_EXIT:
                active_session = session_repo.get_active()
                if active_session:
                    session_repo.end_session(active_session.id)
                db.commit()
                logger.info(f"Session ended on Faculty Exit: {identity.name}")
                return {"status": "session_ended", "session_id": active_session.id if active_session else None}

            # Student scans: enter / exit log mapping
            elif event.event_type in (EventType.STUDENT_ENTER, EventType.STUDENT_EXIT):
                active_session = session_repo.get_active()
                if not active_session:
                    db.commit()
                    logger.info(f"Scan rejected: No active session for {scanned_id}")
                    return {"status": "rejected", "reason": "no_active_session"}

                slot = self.timetable.get_current_slot()

                # Insert raw audit log into scan_logs table
                attendance_repo.log_scan(
                    student_id=scanned_id,
                    scan_type="entry",
                    face_verified=True,
                    confidence=auth_result.confidence,
                    slot=slot,
                )

                # Update legacy student states for live dashboard summary views
                state_machine.transition(scanned_id, StudentState.ACTIVE)

                # Insert present log into attendance table
                attendance_repo.mark_present(scanned_id, active_session.id)

                db.commit()

                logger.info(f"VERIFIED: {identity.name} ({scanned_id}) confidence={auth_result.confidence}")
                return {
                    "status": "verified",
                    "student_id": scanned_id,
                    "student_name": identity.name,
                    "slot": slot,
                    "confidence": auth_result.confidence,
                    "session_active": True,
                }

            db.commit()
            return {"status": "rejected", "reason": "unhandled_event"}

        except Exception as e:
            db.rollback()
            logger.error(f"Database transaction failed: {e}. Changes rolled back.")
            raise e

    def get_status(self, db: DBSession) -> dict:
        """Dashboard-friendly status snapshot."""
        state_machine = StudentStateMachine(db)
        return {
            "current_slot": self.timetable.get_current_slot(),
            "is_break": self.timetable.is_break(),
            "active_students": state_machine.get_active_students(),
            "active_count": len(state_machine.get_active_students()),
            "profiles_loaded": self.face_service.profile_count,
        }
