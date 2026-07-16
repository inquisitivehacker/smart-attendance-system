"""
Attendance repository — database access for attendance records and scan logs.
Replaces the prototype's CSV append with queryable SQLite storage.
"""
from datetime import datetime

from sqlalchemy.orm import Session as DBSession

from src.models.attendance import Attendance
from src.models.scan_log import ScanLog


class AttendanceRepository:
    def __init__(self, db: DBSession):
        self.db = db

    # --- Attendance Records ---


    def upsert_attendance(self, record) -> Attendance:
        """
        Idempotent upsert of an AttendanceRecord into the database.
        Does NOT commit the transaction (orchestrated by the caller).
        """
        existing = (
            self.db.query(Attendance)
            .filter(
                Attendance.student_id == record.student_id,
                Attendance.session_id == record.session_id,
            )
            .first()
        )
        now = datetime.utcnow().isoformat()
        if existing:
            existing.status = record.status
            existing.attendance_percentage = record.participation_percentage
            existing.duration_seconds = record.participation_seconds
            existing.late_minutes = record.late_minutes
            existing.early_departure_minutes = record.early_departure_minutes
            existing.regularization_required = 1 if record.regularization_required else 0
            existing.policy_version = record.policy_version
            existing.computed_at = record.computed_at.isoformat() if record.computed_at else None
            existing.verified_at = now
            existing.method = "barcode_face"
        else:
            existing = Attendance(
                student_id=record.student_id,
                session_id=record.session_id,
                status=record.status,
                attendance_percentage=record.participation_percentage,
                duration_seconds=record.participation_seconds,
                late_minutes=record.late_minutes,
                early_departure_minutes=record.early_departure_minutes,
                regularization_required=1 if record.regularization_required else 0,
                policy_version=record.policy_version,
                computed_at=record.computed_at.isoformat() if record.computed_at else None,
                verified_at=now,
                method="barcode_face",
                created_at=now,
            )
            self.db.add(existing)
        self.db.flush()
        return existing


    def get_by_session(self, session_id: int) -> list[Attendance]:
        return (
            self.db.query(Attendance)
            .filter(Attendance.session_id == session_id)
            .all()
        )

    def get_student_today(self, student_id: str) -> list[Attendance]:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return (
            self.db.query(Attendance)
            .filter(
                Attendance.student_id == student_id,
                Attendance.created_at.like(f"{today}%"),
            )
            .all()
        )

    # --- Scan Logs (Audit Trail) ---

    def log_scan(
        self,
        student_id: str,
        scan_type: str,
        face_verified: bool,
        confidence: float = None,
        slot: str = None,
    ) -> ScanLog:
        log = ScanLog(
            student_id=student_id,
            scan_type=scan_type,
            face_verified=1 if face_verified else 0,
            face_confidence=confidence,
            slot=slot,
            scanned_at=datetime.utcnow(),
        )
        self.db.add(log)
        self.db.flush()
        return log
