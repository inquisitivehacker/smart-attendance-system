from sqlalchemy.orm import Session as DBSession
from src.models.faculty import Faculty


class FacultyRepository:
    def __init__(self, db: DBSession):
        self.db = db

    def get_by_id(self, faculty_id: str) -> Faculty | None:
        return self.db.query(Faculty).filter(Faculty.id == faculty_id).first()
