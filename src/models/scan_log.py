"""
ScanLog model — raw audit trail of every barcode scan event.
Replaces the prototype's CSV log with queryable, indexed storage.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, Text, Float, DateTime

from src.database import Base


class ScanLog(Base):
    __tablename__ = "scan_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Student identifier from barcode
    student_id = Column(Text, nullable=False, index=True)

    # entry | exit | lab | break_out | break_in
    scan_type = Column(Text, nullable=False)

    # Whether face verification succeeded
    face_verified = Column(Integer, default=0, nullable=False)

    # Face recognition distance/confidence score
    face_confidence = Column(Float, nullable=True)

    # Current timetable slot
    slot = Column(Text, nullable=True)

    # Timestamp of scan event
    scanned_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    def __repr__(self):
        return (
            f"<ScanLog("
            f"id={self.id}, "
            f"student_id='{self.student_id}', "
            f"scan_type='{self.scan_type}', "
            f"face_verified={self.face_verified}, "
            f"scanned_at='{self.scanned_at}'"
            f")>"
        )