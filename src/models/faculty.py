"""
Faculty model — lecturers authorized to start/end sessions.
"""
from sqlalchemy import Column, Text
from src.database import Base


class Faculty(Base):
    __tablename__ = "faculty"

    id = Column(Text, primary_key=True)  # Barcode ID e.g. "FAC-01"
    name = Column(Text, nullable=False)
    department = Column(Text)

    def __repr__(self):
        return f"<Faculty {self.id}: {self.name}>"
