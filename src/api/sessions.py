"""Session API routes — faculty starts/ends class sessions."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.repositories.session_repo import SessionRepository
from src.services.timetable_service import TimetableService
from src.schemas.session import SessionStart, SessionResponse

router = APIRouter(prefix="/sessions", tags=["Sessions"])
timetable = TimetableService()


@router.post("/start", response_model=SessionResponse, status_code=201)
def start_session(data: SessionStart, db: Session = Depends(get_db)):
    """Faculty starts a new class session via REST."""
    repo = SessionRepository(db)

    # 1. Resolve faculty_id by name
    from src.models.faculty import Faculty
    faculty = db.query(Faculty).filter(Faculty.name == data.faculty_name).first()
    faculty_id = faculty.id if faculty else "FAC-01"

    # 2. Build formal request object
    from src.schemas.manual_session import SessionStartRequest
    request = SessionStartRequest(
        faculty_id=faculty_id,
        faculty_name=data.faculty_name,
        subject=data.subject,
        room=data.room
    )

    # 3. Call ManualSessionService
    from src.main import manual_session_service
    if not manual_session_service:
        raise HTTPException(status_code=503, detail="ManualSessionService not ready")

    try:
        result = manual_session_service.start_session(request, db)
        db.commit()
        session_id = result.get("session_id")
        return repo.get_by_id(session_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/end", response_model=SessionResponse)
def end_session(db: Session = Depends(get_db)):
    """End the currently active session via REST."""
    repo = SessionRepository(db)
    active = repo.get_active()
    if not active:
        raise HTTPException(status_code=404, detail="No active session")

    from src.main import manual_session_service
    if not manual_session_service:
        raise HTTPException(status_code=503, detail="ManualSessionService not ready")

    try:
        manual_session_service.end_session(db)
        db.commit()
        return repo.get_by_id(active.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))




@router.get("/active", response_model=SessionResponse | None)
def get_active_session(db: Session = Depends(get_db)):
    """Get the currently active session, if any."""
    repo = SessionRepository(db)
    return repo.get_active()


@router.get("/today", response_model=list[SessionResponse])
def get_today_sessions(db: Session = Depends(get_db)):
    """List all sessions for today."""
    repo = SessionRepository(db)
    return repo.get_today_sessions()
