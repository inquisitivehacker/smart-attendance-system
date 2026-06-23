"""Attendance API routes — scan processing and attendance queries."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.repositories.attendance_repo import AttendanceRepository
from src.schemas.attendance import AttendanceResponse, ScanResultResponse, AttendanceScanRequest

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.post("/test-scan")
def test_process_scan(data: AttendanceScanRequest, db: Session = Depends(get_db)):
    """Temporary testing endpoint to validate attendance logic without hardware."""
    from src.main import attendance_engine
    if not attendance_engine:
        raise HTTPException(status_code=503, detail="Attendance engine not ready")
    
    # Call the EXACT same logic used by hardware_loop.py, bypassing camera input
    result = attendance_engine.process_scan(
        scanned_id=data.student_id, 
        frame=None, 
        db=db, 
        skip_face_verification=True
    )

    # Handle success/failure responses based on the engine's result
    if result.get("status") == "verified":
        # Scenario 1: Active Session Success
        from src.repositories.session_repo import SessionRepository
        session_repo = SessionRepository(db)
        active_session = session_repo.get_active()
        
        return {
            "success": True,
            "student_id": data.student_id,
            "session_id": active_session.id if active_session else None,
            "attendance_record_created": True,
            "engine_result": result
        }
    elif result.get("status") == "duplicate":
        return {
            "success": False,
            "error": "Duplicate scan attempt",
            "details": result.get("reason")
        }
    elif result.get("status") == "rejected":
        if result.get("reason") == "no_active_session":
            return {
                "success": False,
                "error": "No active session",
                "details": "Scan rejected immediately because no session is running."
            }
        return {
            "success": False,
            "error": result.get("reason", "Validation failed")
        }
    else:
        return {
            "success": False,
            "error": "Scan denied",
            "details": result
        }



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
