from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database import get_db
from src.models.student import Student
from src.models.attendance import Attendance
from src.models.scan_log import ScanLog
from src.models.session import Session as ClassroomSession

router = APIRouter(tags=["Dashboard"])

@router.get("/dashboard/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    # Total students enrolled
    total_students = db.query(Student).count()
    
    # Active Session details
    active_session = db.query(ClassroomSession).filter(ClassroomSession.is_active == True).first()
    
    present_students = 0
    if active_session:
        present_students = db.query(Attendance).filter(
            Attendance.session_id == active_session.id,
            Attendance.status == "PRESENT"
        ).count()
        
    absent_students = total_students - present_students if total_students > 0 else 0
    attendance_percentage = (present_students / total_students * 100) if total_students > 0 else 0
    
    # Scan metrics for today
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    successful_scans = db.query(ScanLog).filter(
        ScanLog.face_verified == 1,
        ScanLog.scanned_at.like(f"{today}%")
    ).count()
    
    failed_scans = db.query(ScanLog).filter(
        ScanLog.face_verified == 0,
        ScanLog.scanned_at.like(f"{today}%")
    ).count()
    
    return {
        "active_session": {
            "id": active_session.id if active_session else None,
            "subject": active_session.subject if active_session else None,
            "faculty": active_session.faculty if active_session else None,
            "room": active_session.room if active_session else None,
            "start_time": active_session.start_time if active_session else None,
        },
        "attendance_metrics": {
            "total_students": total_students,
            "present_students": present_students,
            "absent_students": absent_students,
            "attendance_percentage": round(attendance_percentage, 1)
        },
        "scan_metrics": {
            "successful_scans_today": successful_scans,
            "failed_scans_today": failed_scans
        }
    }
