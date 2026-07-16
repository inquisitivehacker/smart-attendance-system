"""
Attendance model — one record per student per session.
This is the derived business record (not the raw scan log).
"""
from sqlalchemy import Column, Integer, Text, Float, UniqueConstraint
from src.database import Base


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Text, nullable=False)
    session_id = Column(Integer, nullable=False)
    status = Column(Text, nullable=False)  # PRESENT | ABSENT | LATE | UNVERIFIED
    attendance_percentage = Column(Float, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    late_minutes = Column(Integer, nullable=True)
    early_departure_minutes = Column(Integer, nullable=True)
    regularization_required = Column(Integer, nullable=True)
    policy_version = Column(Text, nullable=True)
    computed_at = Column(Text, nullable=True)
    verified_at = Column(Text)  # When face was verified
    method = Column(Text, default="barcode_face")  # barcode_face | manual_override
    created_at = Column(Text)


    __table_args__ = (
        UniqueConstraint("student_id", "session_id", name="uq_student_session"),
    )

    def __repr__(self):
        return f"<Attendance {self.student_id} session={self.session_id}: {self.status}>"
