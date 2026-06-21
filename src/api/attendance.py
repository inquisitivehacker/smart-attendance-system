"""Attendance API routes — scan processing and attendance queries."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.repositories.attendance_repo import AttendanceRepository
from src.schemas.attendance import AttendanceResponse, ScanResultResponse

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.get("/session/{session_id}", response_model=list[AttendanceResponse])
def get_session_attendance(session_id: int, db: Session = Depends(get_db)):
    """Get all attendance records for a specific session."""
    repo = AttendanceRepository(db)
    records = repo.get_by_session(session_id)
    if not records:
        raise HTTPException(status_code=404, detail="No records found for this session")
    return records


@router.get("/student/{student_id}/today", response_model=list[AttendanceResponse])
def get_student_today(student_id: str, db: Session = Depends(get_db)):
    """Get today's attendance for a specific student."""
    repo = AttendanceRepository(db)
    return repo.get_student_today(student_id)


@router.get("/status")
def get_engine_status(db: Session = Depends(get_db)):
    """Get the current attendance engine status (slot, active students, etc.)."""
    from src.main import attendance_engine
    if not attendance_engine:
        raise HTTPException(status_code=503, detail="Attendance engine not ready")
    return attendance_engine.get_status(db)


@router.get("/live")
def get_live_attendance(limit: int = 50, db: Session = Depends(get_db)):
    """Get the most recent scan logs for the live monitor."""
    from src.models.scan_log import ScanLog
    from src.models.student import Student
    
    recent_scans = (
        db.query(ScanLog, Student.name)
        .outerjoin(Student, ScanLog.student_id == Student.id)
        .order_by(ScanLog.scanned_at.desc())
        .limit(limit)
        .all()
    )
    
    results = []
    for log, student_name in recent_scans:
        results.append({
            "id": log.id,
            "student_id": log.student_id,
            "student_name": student_name or "Unknown Student",
            "scan_type": log.scan_type,
            "face_verified": bool(log.face_verified),
            "face_confidence": log.face_confidence,
            "slot": log.slot,
            "scanned_at": log.scanned_at
        })
        
    return results
