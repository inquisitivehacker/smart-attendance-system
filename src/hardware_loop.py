"""
Hardware Loop Runner
Directly coordinates the scanner, camera, and attendance engine without HTTP overhead.
Includes an async bounded queue to handle scan bursts.
"""
import time
import queue
import signal
import sys
import threading
import logging

from src.config import settings
from src.database import init_db, SessionLocal
from src.services.face_service import FaceService
from src.services.attendance_engine import AttendanceEngine
from src.services.camera_service import CameraService
from src.services.scanner_service import get_scanner_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

class HardwareLoop:
    def __init__(self):
        self.running = False
        self.scan_queue = queue.Queue(maxsize=200)
        
        # Initialize Services
        logger.info("Initializing Database...")
        init_db()
        
        logger.info("Loading Face Profiles...")
        self.face_service = FaceService(
            known_faces_dir=settings.known_faces_dir,
            tolerance=settings.face_tolerance
        )
        
        logger.info("Initializing Engine and Hardware Services...")
        from src.services.identity_service import IdentityService
        from src.services.event_resolver import EventResolver
        from src.services.presence_engine import PresenceEngine
        from src.services.session_manager import SessionManager
        from src.services.manual_session_service import ManualSessionService
        self.identity_service = IdentityService(face_service=self.face_service)
        self.event_resolver = EventResolver()
        self.presence_engine = PresenceEngine()
        self.session_manager = SessionManager()
        self.manual_session_service = ManualSessionService(
            presence_engine=self.presence_engine,
            session_manager=self.session_manager
        )
        self.engine = AttendanceEngine(
            face_service=self.face_service,
            identity_service=self.identity_service,
            event_resolver=self.event_resolver,
            presence_engine=self.presence_engine,
            session_manager=self.session_manager
        )
        
        # Run RuntimeRecoveryService to rebuild states and log reports/warnings
        from src.services.runtime_recovery_service import RuntimeRecoveryService
        db = SessionLocal()
        try:
            recovery_svc = RuntimeRecoveryService()
            recovery_svc.recover_runtime(self.presence_engine, self.session_manager, db)
        except Exception as e:
            logger.error(f"Runtime recovery failed on startup: {e}")
        finally:
            db.close()

        self.camera = CameraService(camera_index=settings.camera_index)




        self.scanner = get_scanner_service()
        
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)

    def start(self):
        self.running = True
        
        # Setup signals for graceful shutdown
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
        
        # Start hardware
        self.camera.start()
        self.scanner.start()
        
        # Start background threads
        self.worker_thread.start()
        self.heartbeat_thread.start()
        
        logger.info("Hardware Loop Active. Waiting for scans...")
        self._scanner_loop()

    def _heartbeat_loop(self):
        """Runs in background. Updates the heartbeat table every 30 seconds."""
        from src.models.system_status import SystemStatus
        from datetime import datetime
        
        while self.running:
            db = SessionLocal()
            try:
                status = db.query(SystemStatus).filter(SystemStatus.component == "hardware_loop").first()
                if not status:
                    status = SystemStatus(component="hardware_loop", status="ONLINE")
                    db.add(status)
                else:
                    status.last_heartbeat = datetime.utcnow()
                    status.status = "ONLINE"
                db.commit()
            except Exception as e:
                logger.error(f"Heartbeat failed: {e}")
            finally:
                db.close()
                
            # Sleep 30s in small chunks to allow quick shutdown
            for _ in range(30):
                if not self.running:
                    break
                time.sleep(1)

    def _scanner_loop(self):
        """Runs in the main thread. Pushes scans to the queue."""
        while self.running:
            barcode = self.scanner.read_barcode()
            if barcode and self.running:
                frame = self.camera.get_latest_frame()
                if frame is None:
                    logger.warning(f"Scan '{barcode}' ignored: Camera not ready.")
                    continue
                
                try:
                    self.scan_queue.put_nowait((barcode, frame))
                    logger.info(f"Queued scan: {barcode} (Queue size: {self.scan_queue.qsize()})")
                except queue.Full:
                    logger.error(f"Scan queue full! Dropped scan: {barcode}")

    def _worker_loop(self):
        """Runs in background. Processes scans via AttendanceEngine."""
        while self.running or not self.scan_queue.empty():
            try:
                # 1 second timeout allows checking self.running gracefully
                barcode, frame = self.scan_queue.get(timeout=1.0)
            except queue.Empty:
                continue
                
            db = SessionLocal()
            try:
                result = self.engine.process_scan(barcode, frame, db)
                self._display_result(result)
            except Exception as e:
                logger.error(f"Error processing scan {barcode}: {e}")
            finally:
                db.close()
                self.scan_queue.task_done()

    def _display_result(self, result: dict):
        """Console output representing a physical UI/buzzer feedback."""
        status = result.get("status")
        if status == "verified":
            logger.info(f"✅ SUCCESS: {result.get('student_name')} ({result.get('student_id')}) - {result.get('slot')}")
        elif status == "denied":
            logger.warning(f"❌ DENIED: {result.get('student_name')} ({result.get('student_id')}) - Face Mismatch")
        elif status == "duplicate":
            logger.info(f"⏳ DUPLICATE: {result.get('student_name')} - Wait {result.get('reason').split('_')[1]}")
        else:
            logger.warning(f"⚠️ REJECTED: {result.get('reason')}")

    def shutdown(self, signum=None, frame=None):
        if not self.running:
            return
            
        logger.info("\nInitiating Graceful Shutdown...")
        self.running = False
        
        logger.info("Stopping Scanner...")
        self.scanner.stop()
        
        logger.info("Stopping Camera...")
        self.camera.stop()
        
        if not self.scan_queue.empty():
            logger.info(f"Flushing Queue ({self.scan_queue.qsize()} items remaining)...")
            # Give the worker thread time to empty the queue
            timeout = time.time() + 10  # 10s max wait
            while not self.scan_queue.empty() and time.time() < timeout:
                time.sleep(0.5)
            
        logger.info("Hardware Loop Terminated cleanly.")
        sys.exit(0)

if __name__ == "__main__":
    if settings.hardware_mode:
        app = HardwareLoop()
        app.start()
    else:
        logger.error("HARDWARE_MODE is false. Run FastAPI instead.")
