"""
Face recognition service — wraps the face_recognition library.
Preserves: average encoding, 1/4 scale downsampling, distance matching.
All core logic from prototype lines 92-113 and 186-200.
"""
import os
import glob
import logging

import cv2
import numpy as np
import face_recognition

logger = logging.getLogger(__name__)


class FaceService:
    def __init__(self, known_faces_dir: str = "known_faces", tolerance: float = 0.50):
        self.tolerance = tolerance
        self.known_encodings: list[np.ndarray] = []
        self.known_ids: list[str] = []
        self._load_faces(known_faces_dir)

    def _load_faces(self, faces_dir: str):
        """
        Load and compute average face encodings.
        Preserved from prototype lines 92-113.
        """
        if not os.path.isdir(faces_dir):
            logger.warning(f"Known faces directory not found: {faces_dir}")
            return

        for person_folder in os.listdir(faces_dir):
            person_path = os.path.join(faces_dir, person_folder)
            if not os.path.isdir(person_path):
                continue

            encodings = []
            # Load all jpg/png/jpeg images (preserved from prototype)
            valid_images = (
                glob.glob(f"{person_path}/*.jpg")
                + glob.glob(f"{person_path}/*.png")
                + glob.glob(f"{person_path}/*.jpeg")
            )

            for img_path in valid_images:
                try:
                    image = face_recognition.load_image_file(img_path)
                    face_enc = face_recognition.face_encodings(image)
                    if face_enc:
                        encodings.append(face_enc[0])
                except Exception as e:
                    logger.error(f"Failed to process {img_path}: {e}")

            if encodings:
                # Average encoding for better accuracy (preserved from prototype)
                self.known_encodings.append(np.mean(encodings, axis=0))
                self.known_ids.append(person_folder)
                logger.info(f"Loaded profile: {person_folder} ({len(encodings)} photos)")

        logger.info(f"Face database ready: {len(self.known_ids)} profiles loaded")

    def verify(self, frame: np.ndarray, expected_id: str) -> tuple[bool, float]:
        """
        Verify that the face in frame matches the expected student ID.
        Preserved from prototype lines 186-200.
        Returns (verified: bool, confidence: float).
        """
        if len(self.known_encodings) == 0:
            return False, 0.0

        # 1/4 scale for speed (preserved from prototype)
        small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        face_locs = face_recognition.face_locations(rgb)
        if not face_locs:
            return False, 0.0

        face_encs = face_recognition.face_encodings(rgb, face_locs)
        if not face_encs:
            return False, 0.0

        dists = face_recognition.face_distance(self.known_encodings, face_encs[0])
        if len(dists) == 0:
            return False, 0.0

        min_dist = float(min(dists))
        if min_dist < self.tolerance:
            match_idx = int(np.argmin(dists))
            if self.known_ids[match_idx] == expected_id:
                return True, round(1.0 - min_dist, 3)

        return False, 0.0

    @property
    def profile_count(self) -> int:
        return len(self.known_ids)
