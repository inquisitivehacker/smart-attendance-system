"""
Student repository — database access for student records.
"""
from sqlalchemy.orm import Session as DBSession

from src.models.student import Student


class StudentRepository:
    def __init__(self, db: DBSession):
        self.db = db

    def get_by_id(self, student_id: str) -> Student | None:
        return self.db.query(Student).filter(Student.id == student_id).first()

    def get_all(self) -> list[Student]:
        return self.db.query(Student).all()

    def create(
        self, student_id: str, name: str, department: str = None
    ) -> Student:
        from datetime import datetime

        student = Student(
            id=student_id,
            name=name,
            department=department,
            created_at=datetime.utcnow().isoformat(),
        )
        self.db.add(student)
        self.db.commit()
        self.db.refresh(student)
        return student

    def mark_face_enrolled(self, student_id: str):
        self.db.query(Student).filter(Student.id == student_id).update(
            {"face_enrolled": 1}
        )
        self.db.commit()

    def exists(self, student_id: str) -> bool:
        return self.get_by_id(student_id) is not None
