import cv2
import threading
import time
import logging

logger = logging.getLogger(__name__)


class CameraService:
    """
    Runs a background thread to continuously capture frames from the camera.
    Provides instant access to the latest frame, completely decoupling camera I/O
    from face verification logic.
    """
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None
        self.latest_frame = None
        self._lock = threading.Lock()
        self._running = False
        self._thread = None

    def start(self):
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            logger.error(f"Failed to open camera {self.camera_index}")
            return
        
        # Warmup: discard initial frames
        for _ in range(10):
            self.cap.read()
            
        self._running = True
        self._thread = threading.Thread(target=self._update, daemon=True)
        self._thread.start()
        logger.info(f"CameraService started on index {self.camera_index}")

    def _update(self):
        while self._running:
            if not self.cap:
                time.sleep(0.1)
                continue
                
            ret, frame = self.cap.read()
            if ret:
                with self._lock:
                    self.latest_frame = frame.copy()
            else:
                logger.warning("Camera disconnected. Attempting to reconnect...")
                self.cap.release()
                time.sleep(1)
                self.cap = cv2.VideoCapture(self.camera_index)
                if self.cap.isOpened():
                    logger.info("Camera reconnected successfully.")

    def get_latest_frame(self):
        """Returns a copy of the latest frame."""
        with self._lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy()
            return None

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()
            self.cap = None
        logger.info("CameraService stopped.")
