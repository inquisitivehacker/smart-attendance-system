"""
Student model — enrolled students with barcode IDs.
"""
from sqlalchemy import Column, Text, Integer
from src.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Text, primary_key=True)  # Barcode ID e.g. "SET-12584"
    name = Column(Text, nullable=False)
    department = Column(Text)
    face_enrolled = Column(Integer, default=0)  # 0/1 boolean
    created_at = Column(Text)

    def __repr__(self):
        return f"<Student {self.id}: {self.name}>"
