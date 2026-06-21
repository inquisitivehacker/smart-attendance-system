from datetime import datetime

from sqlalchemy import Column, Text, DateTime

from src.database import Base


class StudentState(Base):
    __tablename__ = "student_states"

    student_id = Column(Text, primary_key=True)

    state = Column(
        Text,
        nullable=False,
        default="OFFLINE"
    )

    current_location = Column(
        Text,
        nullable=True
    )

    last_updated = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    def __repr__(self):
        return (
            f"<StudentState("
            f"student_id='{self.student_id}', "
            f"state='{self.state}', "
            f"location='{self.current_location}'"
            f")>"
        )