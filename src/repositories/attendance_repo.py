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

    def mark_present(
        self, student_id: str, session_id: int, method: str = "barcode_face", percentage: float = None, duration: int = None
    ) -> Attendance:
        """Upsert: update if exists, create if not."""
        existing = (
            self.db.query(Attendance)
            .filter(
                Attendance.student_id == student_id,
                Attendance.session_id == session_id,
            )
            .first()
        )
        now = datetime.now().isoformat()
        if existing:
            existing.status = "PRESENT"
            existing.verified_at = now
            existing.method = method
            if percentage is not None:
                existing.attendance_percentage = percentage
            if duration is not None:
                existing.duration_seconds = duration
        else:
            existing = Attendance(
                student_id=student_id,
                session_id=session_id,
                status="PRESENT",
                verified_at=now,
                method=method,
                attendance_percentage=percentage,
                duration_seconds=duration,
                created_at=now,
            )
            self.db.add(existing)
        self.db.commit()
        return existing


    def get_by_session(self, session_id: int) -> list[Attendance]:
        return (
            self.db.query(Attendance)
            .filter(Attendance.session_id == session_id)
            .all()
        )

    def get_student_today(self, student_id: str) -> list[Attendance]:
        today = datetime.now().strftime("%Y-%m-%d")
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
        self.db.commit()
        return log

    def get_last_scan(self, student_id: str) -> ScanLog | None:
        return (
            self.db.query(ScanLog)
            .filter(ScanLog.student_id == student_id)
            .order_by(ScanLog.id.desc())
            .first()
        )

    def get_last_successful_scan(self, student_id: str) -> ScanLog | None:
        """Fetch the most recent scan where face was verified successfully."""
        return (
            self.db.query(ScanLog)
            .filter(
                ScanLog.student_id == student_id,
                ScanLog.face_verified == 1
            )
            .order_by(ScanLog.id.desc())
            .first()
        )
