"""
Smart Attendance System — FastAPI Application Entry Point.

Usage:
    uvicorn src.main:app --reload --port 8000
"""
import logging

import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.config import settings
from src.database import init_db
from src.services.face_service import FaceService
from src.services.attendance_engine import AttendanceEngine
from src.api import students, sessions, attendance, dashboard, reports

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# --- App ---
app = FastAPI(
    title="Smart Attendance System",
    description="Barcode + Face verification attendance for university classrooms",
    version="1.0.0-pilot",
)

# CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development. Allow all.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global Services (initialized on startup) ---
face_service: FaceService | None = None
attendance_engine: AttendanceEngine | None = None


@app.on_event("startup")
def startup():
    global face_service, attendance_engine

    logger.info("--- SMART ATTENDANCE SYSTEM BOOT ---")

    # 1. Initialize database
    init_db()
    logger.info("Database initialized")

    # 2. Load face recognition profiles
    face_service = FaceService(
        known_faces_dir=settings.known_faces_dir,
        tolerance=settings.face_tolerance,
    )
    logger.info(f"Face profiles loaded: {face_service.profile_count}")

    # 3. Create IdentityService
    from src.services.identity_service import IdentityService
    identity_service = IdentityService(face_service=face_service)
    logger.info("Identity service initialized")

    # 4. Create attendance engine
    attendance_engine = AttendanceEngine(face_service=face_service, identity_service=identity_service)
    logger.info("Attendance engine ready")

    logger.info(f"Server starting on {settings.host}:{settings.port}")
    logger.info("--- SYSTEM READY ---")



# --- Include Routers ---
app.include_router(dashboard.router, prefix="/api")
app.include_router(students.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(attendance.router, prefix="/api")
app.include_router(reports.router, prefix="/api")


@app.get("/api/health", tags=["Health"])
def health_check():
    """Health check endpoint validating API and Hardware Loop heartbeat."""
    from src.database import SessionLocal
    from src.models.system_status import SystemStatus
    from datetime import datetime
    
    db = SessionLocal()
    try:
        # Check heartbeat
        status = db.query(SystemStatus).filter(SystemStatus.component == "hardware_loop").first()
        hardware_status = "OFFLINE"
        
        if status:
            delta = (datetime.utcnow() - status.last_heartbeat).total_seconds()
            if delta <= 60:
                hardware_status = "ONLINE"
            else:
                hardware_status = "STALE"
                
        return {
            "api_status": "ONLINE",
            "hardware_loop": hardware_status,
            "version": "1.0.0-pilot",
            "profiles_loaded": face_service.profile_count if face_service else 0,
        }
    finally:
        db.close()


@app.get("/api/slots", tags=["Timetable"])
def get_slots():
    """Get all timetable slots."""
    from src.services.timetable_service import TimetableService
    return TimetableService().get_all_slots()

# --- Serve React Frontend ---
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
assets_path = os.path.join(frontend_dist, "assets")

if os.path.exists(assets_path):
    app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

from fastapi import HTTPException

@app.get("/{file_name:path}")
async def serve_spa(file_name: str):
    if file_name.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
        
    file_path = os.path.join(frontend_dist, file_name)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
        
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
        
    raise HTTPException(status_code=404, detail="Frontend not built")
