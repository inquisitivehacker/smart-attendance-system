"""
Attendance Engine — the core business logic.
Phase 2 Update: Cooldown tracking and state machine moved to the database.
"""
from datetime import datetime
import logging

from sqlalchemy.orm import Session as DBSession

from src.config import settings
from src.repositories.student_repo import StudentRepository
from src.repositories.session_repo import SessionRepository
from src.repositories.attendance_repo import AttendanceRepository
from src.services.face_service import FaceService
from src.services.timetable_service import TimetableService
from src.services.state_machine import StudentStateMachine, StudentState

logger = logging.getLogger(__name__)


class AttendanceEngine:
    """
    Stateful engine managing attendance verification for a single classroom.
    Instantiated once at app startup; shared across requests.
    """

    def __init__(self, face_service: FaceService):
        self.face_service = face_service
        self.timetable = TimetableService()

    def process_scan(self, scanned_id: str, frame, db: DBSession) -> dict:
        """
        Main entry point — called by the hardware loop worker thread.
        Returns a result dict with status and details.
        """
        attendance_repo = AttendanceRepository(db)
        state_machine = StudentStateMachine(db)

        # 1. Validate barcode format
        if not self._validate_barcode(scanned_id):
            logger.info(f"Rejected invalid barcode: {scanned_id}")
            return {"status": "rejected", "reason": "invalid_format"}

        # 2. Check student exists in DB
        student_repo = StudentRepository(db)
        student = student_repo.get_by_id(scanned_id)
        if not student:
            logger.warning(f"Unknown student ID: {scanned_id}")
            return {"status": "rejected", "reason": "unknown_student", "student_id": scanned_id}

        # 3. Database-backed Cooldown check (only successful scans trigger cooldown)
        last_scan = attendance_repo.get_last_successful_scan(scanned_id)
        if last_scan and isinstance(last_scan.scanned_at, datetime):
            delta = (datetime.utcnow() - last_scan.scanned_at).total_seconds()
            if delta < settings.cooldown_seconds:
                remaining = int((settings.cooldown_seconds - delta) / 60)
                logger.info(f"Duplicate scan blocked: {scanned_id} (wait {remaining}m)")
                return {
                    "status": "duplicate",
                    "reason": f"wait_{remaining}m",
                    "student_id": scanned_id,
                    "student_name": student.name,
                }

        # 4. Face verification
        verified, confidence = self.face_service.verify(frame, scanned_id)

        # 5. Get current slot
        slot = self.timetable.get_current_slot()

        # 6. Log the raw scan event (audit trail)
        attendance_repo.log_scan(
            student_id=scanned_id,
            scan_type="entry",
            face_verified=verified,
            confidence=confidence,
            slot=slot,
        )

        if verified:
            # Transition student state via DB repo
            state_machine.transition(scanned_id, StudentState.ACTIVE)

            # Mark attendance for active session if one exists
            session_repo = SessionRepository(db)
            active_session = session_repo.get_active()
            if active_session:
                attendance_repo.mark_present(scanned_id, active_session.id)

            logger.info(f"VERIFIED: {student.name} ({scanned_id}) confidence={confidence}")
            return {
                "status": "verified",
                "student_id": scanned_id,
                "student_name": student.name,
                "slot": slot,
                "confidence": confidence,
                "session_active": active_session is not None,
            }
        else:
            logger.warning(f"DENIED: {scanned_id} — face mismatch (confidence={confidence})")
            return {
                "status": "denied",
                "student_id": scanned_id,
                "student_name": student.name,
                "reason": "face_mismatch",
                "confidence": confidence,
            }

    def _validate_barcode(self, barcode: str) -> bool:
        if len(barcode) > 12 or len(barcode) < 5:
            return False
        if not barcode.startswith(("21", "22", "23", "SET")):
            return False
        return True

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
