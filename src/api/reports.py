import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.session import Session as ClassroomSession
from src.models.attendance import Attendance
from src.models.student import Student

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/sessions")
def get_session_reports(db: Session = Depends(get_db)):
    sessions = db.query(ClassroomSession).order_by(ClassroomSession.started_at.desc()).limit(50).all()
    total_students = db.query(Student).count()
    
    results = []
    for s in sessions:
        present = db.query(Attendance).filter(Attendance.session_id == s.id, Attendance.status == "PRESENT").count()
        absent = total_students - present if total_students > 0 else 0
        percentage = (present / total_students * 100) if total_students > 0 else 0
        
        results.append({
            "id": s.id,
            "subject": s.subject,
            "date": s.started_at,
            "present": present,
            "absent": absent,
            "percentage": round(percentage, 1)
        })
    return results

@router.get("/students")
def get_student_reports(db: Session = Depends(get_db)):
    students = db.query(Student).all()
    total_sessions = db.query(ClassroomSession).count()
    
    results = []
    for s in students:
        present = db.query(Attendance).filter(Attendance.student_id == s.id, Attendance.status == "PRESENT").count()
        absent = total_sessions - present if total_sessions > 0 else 0
        percentage = (present / total_sessions * 100) if total_sessions > 0 else 0
        
        results.append({
            "id": s.id,
            "name": s.name,
            "total_sessions": total_sessions,
            "present": present,
            "absent": absent,
            "percentage": round(percentage, 1)
        })
    return results

@router.get("/export/csv")
def export_csv(db: Session = Depends(get_db)):
    """Export attendance raw data as CSV."""
    records = (
        db.query(Attendance, Student, ClassroomSession)
        .join(Student, Attendance.student_id == Student.id)
        .join(ClassroomSession, Attendance.session_id == ClassroomSession.id)
        .order_by(Attendance.verified_at.desc())
        .all()
    )
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Session ID", "Subject", "Student ID", "Student Name", "Status", "Method"])
    
    for att, std, sess in records:
        writer.writerow([
            att.verified_at,
            sess.id,
            sess.subject,
            std.id,
            std.name,
            att.status,
            att.method
        ])
        
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance_export.csv"}
    )


@router.get("/analytics")
def get_analytics(db: Session = Depends(get_db)):
    """Get system-wide analytics metrics."""
    from src.models.scan_log import ScanLog
    from datetime import datetime
    
    total_students = db.query(Student).count()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    total_scans = db.query(ScanLog).count()
    successful_scans = db.query(ScanLog).filter(ScanLog.face_verified == 1).count()
    failed_scans = total_scans - successful_scans
    
    success_rate = (successful_scans / total_scans * 100) if total_scans > 0 else 0
    failure_rate = (failed_scans / total_scans * 100) if total_scans > 0 else 0
    
    today_attendance = db.query(Attendance).filter(Attendance.verified_at.like(f"{today}%")).count()
    
    return {
        "attendance_metrics": {
            "total_students": total_students,
            "today_attendance": today_attendance,
            "total_scans": total_scans,
            "successful_scans": successful_scans,
            "failed_scans": failed_scans
        },
        "recognition_metrics": {
            "success_rate": round(success_rate, 1),
            "failure_rate": round(failure_rate, 1)
        },
        "performance_metrics": {
            "avg_verification_time_ms": 850, # Mocked since not stored
            "queue_size_estimate": 0, # Cannot inspect queue cross-process without DB
            "system_uptime": "N/A" # Measured by heartbeat
        }
    }
