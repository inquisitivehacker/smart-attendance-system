"""
AuthenticationLog model — records all authentication attempts for security logging.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, Text, Float, DateTime
from src.database import Base


class AuthenticationLog(Base):
    __tablename__ = "authentication_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    barcode_scanned = Column(Text, nullable=False)
    resolved_id = Column(Text, nullable=True)
    actor_type = Column(Text, nullable=False)  # STUDENT | FACULTY | UNKNOWN
    face_verified = Column(Integer, nullable=False, default=0)  # 0 | 1 boolean
    face_confidence = Column(Float, nullable=True)
    status = Column(Text, nullable=False)  # SUCCESS | REJECTED_FACE | UNKNOWN_BARCODE | INVALID_FORMAT
    scanned_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<AuthenticationLog {self.id}: {self.barcode_scanned} ({self.status})>"
