"""Student API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.repositories.student_repo import StudentRepository
from src.schemas.student import StudentCreate, StudentResponse

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("")
@router.get("/", response_model=list[StudentResponse])
def list_students(db: Session = Depends(get_db)):
    """List all enrolled students."""
    repo = StudentRepository(db)
    return repo.get_all()


from pydantic import BaseModel
import os
import glob
from src.config import settings

class StudentUpdate(BaseModel):
    name: str | None = None
    department: str | None = None

@router.get("/enrollment")
def get_enrollment_status(db: Session = Depends(get_db)):
    """Get face enrollment status for all students."""
    repo = StudentRepository(db)
    students = repo.get_all()
    
    results = []
    for s in students:
        img_dir = os.path.join(settings.known_faces_dir, s.id)
        count = 0
        if os.path.exists(img_dir):
            count = len(glob.glob(os.path.join(img_dir, "*.jpg"))) + len(glob.glob(os.path.join(img_dir, "*.png")))
            
        if count >= 3:
            status = "Healthy"
        elif count > 0:
            status = "Warning"
        else:
            status = "Missing"
            
        results.append({
            "id": s.id,
            "name": s.name,
            "department": s.department,
            "image_count": count,
            "status": status
        })
        
    return results


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: str, db: Session = Depends(get_db)):
    """Get a student by barcode ID."""
    repo = StudentRepository(db)
    student = repo.get_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.post("")
@router.post("/", response_model=StudentResponse, status_code=201)
def create_student(data: StudentCreate, db: Session = Depends(get_db)):
    """Enroll a new student."""
    repo = StudentRepository(db)
    if repo.exists(data.id):
        raise HTTPException(status_code=409, detail="Student already exists")
    return repo.create(student_id=data.id, name=data.name, department=data.department)


@router.put("/{student_id}", response_model=StudentResponse)
def update_student(student_id: str, data: StudentUpdate, db: Session = Depends(get_db)):
    """Update a student's details."""
    repo = StudentRepository(db)
    student = repo.get_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    if data.name:
        student.name = data.name
    if data.department:
        student.department = data.department
        
    db.commit()
    db.refresh(student)
    return student

@router.delete("/{student_id}", status_code=204)
def delete_student(student_id: str, db: Session = Depends(get_db)):
    """Delete a student."""
    repo = StudentRepository(db)
    student = repo.get_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    db.delete(student)
    db.commit()
