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
    """Faculty starts a new class session."""
    repo = SessionRepository(db)

    # Check if a session is already active
    active = repo.get_active()
    if active:
        raise HTTPException(
            status_code=409,
            detail=f"Session already active: {active.subject} by {active.faculty_name}",
        )

    slot = timetable.get_current_slot()
    session = repo.start_session(
        faculty=data.faculty_name,
        subject=data.subject,
        slot=slot,
        room=data.room,
    )
    return session


@router.post("/end", response_model=SessionResponse)
def end_session(db: Session = Depends(get_db)):
    """End the currently active session."""
    repo = SessionRepository(db)
    active = repo.get_active()
    if not active:
        raise HTTPException(status_code=404, detail="No active session")
    repo.end_session(active.id)
    # Refresh to get updated fields
    return repo.get_by_id(active.id)


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
