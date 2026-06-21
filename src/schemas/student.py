"""Pydantic schemas for Student API."""
from pydantic import BaseModel


class StudentCreate(BaseModel):
    id: str  # Barcode ID
    name: str
    department: str | None = None


class StudentResponse(BaseModel):
    id: str
    name: str
    department: str | None
    face_enrolled: int
    created_at: str | None

    model_config = {"from_attributes": True}
