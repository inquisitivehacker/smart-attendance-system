import tests.test_env  # noqa: F401
import unittest
from datetime import datetime
from unittest.mock import MagicMock

from src.database import init_db, SessionLocal
from src.repositories.presence_state_repo import PresenceStateRepository
from src.repositories.presence_event_repo import PresenceEventRepository
from src.models.presence_event import PresenceEvent as PresenceEventModel
from src.models.student_presence_state import StudentPresenceState
from src.models.session import Session as ClassSession
from src.schemas.identity import AuthenticationResult, Identity, Role, AuthenticationStatus
from src.services.attendance_engine import AttendanceEngine
from src.services.presence_engine import PresenceEngine
from src.services.face_service import FaceService


class TestPresenceTransaction(unittest.TestCase):
    def setUp(self):
        init_db()
        self.db = SessionLocal()
        self.student_id = "SET-12584"

        # Ensure student exists in DB for foreign key constraint
        from src.models.student import Student
        std = self.db.query(Student).filter(Student.id == self.student_id).first()
        if not std:
            std = Student(id=self.student_id, name="Jane Student")
            self.db.add(std)
            self.db.commit()

        # Ensure student presence record is cleared
        rec = self.db.query(StudentPresenceState).filter(StudentPresenceState.student_id == self.student_id).first()
        if rec:
            self.db.delete(rec)
        self.db.query(PresenceEventModel).filter(PresenceEventModel.actor_id == self.student_id).delete()
        self.db.commit()

        # Mock FaceService
        self.face_service = MagicMock(spec=FaceService)
        self.face_service.profile_count = 2

        # Create active session to pass legacy session check
        self.session = self.db.query(ClassSession).filter(ClassSession.status == "active").first()
        if not self.session:
            self.session = ClassSession(
                faculty_name="Dr. Adheem",
                subject="Computer Science",
                slot="Hour 1",
                started_at=datetime.utcnow().isoformat(),
                status="active"
            )
            self.db.add(self.session)
            self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_successful_scan_persists_both_event_and_state(self):
        engine = AttendanceEngine(face_service=self.face_service)

        # Process student scan
        res = engine.process_scan(self.student_id, frame=None, db=self.db, skip_face_verification=True)
        self.assertEqual(res["status"], "verified")

        # Verify event was persisted in database
        events = self.db.query(PresenceEventModel).filter(PresenceEventModel.actor_id == self.student_id).all()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "STUDENT_ENTER")

        # Verify runtime presence state table was updated to INSIDE
        state = self.db.query(StudentPresenceState).filter(StudentPresenceState.student_id == self.student_id).first()
        self.assertIsNotNone(state)
        self.assertEqual(state.presence_state, "INSIDE")

    def test_failed_state_transition_rolls_back_entire_transaction(self):
        # Create a PresenceEngine instance and mock process_event to throw an error
        failing_presence_engine = PresenceEngine()
        failing_presence_engine.process_event = MagicMock(side_effect=Exception("Simulated Database Error"))

        engine = AttendanceEngine(
            face_service=self.face_service,
            presence_engine=failing_presence_engine
        )

        # Process scan and catch error
        with self.assertRaises(Exception) as context:
            engine.process_scan(self.student_id, frame=None, db=self.db, skip_face_verification=True)

        self.assertIn("Simulated Database Error", str(context.exception))

        # Verify that BOTH changes were rolled back and nothing was committed

        # 1. Event store should be empty for this student
        events = self.db.query(PresenceEventModel).filter(PresenceEventModel.actor_id == self.student_id).all()
        self.assertEqual(len(events), 0)

        # 2. State record should NOT exist
        state = self.db.query(StudentPresenceState).filter(StudentPresenceState.student_id == self.student_id).first()
        self.assertIsNone(state)
