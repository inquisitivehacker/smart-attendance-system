"""
Attendance Engine — the core business logic.
Milestone 2 Refactor: Authentication extracted to IdentityService.
"""
from datetime import datetime
import logging

from sqlalchemy.orm import Session as DBSession

from src.config import settings
from src.repositories.student_repo import StudentRepository
from src.repositories.session_repo import SessionRepository
from src.repositories.attendance_repo import AttendanceRepository
from src.services.face_service import FaceService
from src.services.identity_service import IdentityService
from src.services.timetable_service import TimetableService
from src.services.state_machine import StudentStateMachine, StudentState
from src.schemas.identity import AuthenticationStatus, Role

logger = logging.getLogger(__name__)


class AttendanceEngine:
    """
    Stateful engine managing attendance verification for a single classroom.
    Instantiated once at app startup; shared across requests.
    """

    def __init__(self, face_service: FaceService, identity_service: IdentityService = None):
        self.face_service = face_service
        self.identity_service = identity_service or IdentityService(face_service)
        self.timetable = TimetableService()

    def process_scan(self, scanned_id: str, frame, db: DBSession, skip_face_verification: bool = False) -> dict:
        """
        Main entry point — called by the hardware loop worker thread.
        Returns a result dict with status and details.
        """
        attendance_repo = AttendanceRepository(db)
        state_machine = StudentStateMachine(db)
        session_repo = SessionRepository(db)

        # 0. Delegate authentication to IdentityService
        auth_result = self.identity_service.authenticate(scanned_id, frame, db, skip_face_verification)

        # Handle authentication failures
        if not auth_result.authenticated:
            # Commit the transaction so the authentication log is written
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

        # Process faculty scans (authenticated, but ignored for student attendance records)
        identity = auth_result.identity
        if identity.role == Role.FACULTY:
            db.commit()
            logger.info(f"Faculty authenticated: {identity.name} ({scanned_id})")
            return {"status": "rejected", "reason": "faculty_scan_ignored", "name": identity.name}

        # Actor is a STUDENT
        student_name = identity.name

        # 1. Check for active session first!
        active_session = session_repo.get_active()
        if not active_session:
            db.commit()
            logger.info(f"Scan rejected: No active session for {scanned_id}")
            return {"status": "rejected", "reason": "no_active_session"}

        # 2. Database-backed Cooldown check
        last_scan = attendance_repo.get_last_successful_scan(scanned_id)
        if last_scan and isinstance(last_scan.scanned_at, datetime):
            delta = (datetime.utcnow() - last_scan.scanned_at).total_seconds()
            if delta < settings.cooldown_seconds:
                db.commit()
                remaining = int((settings.cooldown_seconds - delta) / 60)
                logger.info(f"Duplicate scan blocked: {scanned_id} (wait {remaining}m)")
                return {
                    "status": "duplicate",
                    "reason": f"wait_{remaining}m",
                    "student_id": scanned_id,
                    "student_name": student_name,
                }

        # 3. Get current slot
        slot = self.timetable.get_current_slot()

        # 4. Log the raw scan event (business auditing trail in scan_logs table)
        attendance_repo.log_scan(
            student_id=scanned_id,
            scan_type="entry",
            face_verified=True,
            confidence=auth_result.confidence,
            slot=slot,
        )

        # 5. Transition student state via DB repo
        state_machine.transition(scanned_id, StudentState.ACTIVE)

        # 6. Mark attendance for the guaranteed active session
        attendance_repo.mark_present(scanned_id, active_session.id)

        # 7. Finalize database transaction
        db.commit()

        logger.info(f"VERIFIED: {student_name} ({scanned_id}) confidence={auth_result.confidence}")
        return {
            "status": "verified",
            "student_id": scanned_id,
            "student_name": student_name,
            "slot": slot,
            "confidence": auth_result.confidence,
            "session_active": True,
        }

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
