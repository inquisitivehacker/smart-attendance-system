import unittest
from datetime import datetime
from unittest.mock import MagicMock

from src.database import init_db, SessionLocal
from src.repositories.presence_state_repo import PresenceStateRepository
from src.repositories.presence_event_repo import PresenceEventRepository
from src.models.presence_event import PresenceEvent as PresenceEventModel
from src.models.student_presence_state import StudentPresenceState
from src.models.session import Session as ClassSession
from src.models.faculty import Faculty
from src.schemas.identity import Role
from src.services.attendance_engine import AttendanceEngine
from src.services.session_manager import SessionManager
from src.services.face_service import FaceService


class TestSessionTransaction(unittest.TestCase):
    def setUp(self):
        init_db()
        self.db = SessionLocal()
        self.faculty_id = "FAC-01"

        # Ensure faculty is in DB
        fac = self.db.query(Faculty).filter(Faculty.id == self.faculty_id).first()
        if not fac:
            fac = Faculty(id=self.faculty_id, name="Dr. Adheem", department="CSE", email="cse@test.com")
            self.db.add(fac)
            self.db.commit()

        # Clean database records
        self.db.query(PresenceEventModel).filter(PresenceEventModel.actor_id == self.faculty_id).delete()
        self.db.query(ClassSession).filter(ClassSession.status == "active").delete()
        self.db.commit()

        self.face_service = MagicMock(spec=FaceService)
        self.face_service.profile_count = 2

    def tearDown(self):
        self.db.close()

    def test_session_manager_starts_and_commits_successfully(self):
        engine = AttendanceEngine(face_service=self.face_service)

        # Process faculty enters
        res = engine.process_scan(self.faculty_id, frame=None, db=self.db, skip_face_verification=True)
        self.assertEqual(res["status"], "session_started")

        # Verify event was persisted
        events = self.db.query(PresenceEventModel).filter(PresenceEventModel.actor_id == self.faculty_id).all()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "FACULTY_ENTER")

        # Verify active session was persisted
        active = self.db.query(ClassSession).filter(ClassSession.status == "active").first()
        self.assertIsNotNone(active)
        self.assertEqual(active.faculty_id, self.faculty_id)

    def test_session_manager_failure_rolls_back_everything(self):
        # Create a SessionManager that throws an exception
        failing_session_manager = SessionManager()
        failing_session_manager.handle_event = MagicMock(side_effect=Exception("Session Manager Exploded"))

        engine = AttendanceEngine(
            face_service=self.face_service,
            session_manager=failing_session_manager
        )

        # Run process scan and catch exception
        with self.assertRaises(Exception) as context:
            engine.process_scan(self.faculty_id, frame=None, db=self.db, skip_face_verification=True)

        self.assertIn("Session Manager Exploded", str(context.exception))

        # Verify that BOTH the event log and session creation are rolled back:

        # 1. Event ledger should be empty
        events = self.db.query(PresenceEventModel).filter(PresenceEventModel.actor_id == self.faculty_id).all()
        self.assertEqual(len(events), 0)

        # 2. Session should not be started
        active = self.db.query(ClassSession).filter(ClassSession.status == "active").first()
        self.assertIsNone(active)


if __name__ == "__main__":
    unittest.main()
