import tests.test_env  # noqa: F401
import unittest
from datetime import datetime, timedelta
from src.database import init_db, SessionLocal
from src.models.session import Session as ClassSession
from src.models.faculty import Faculty
from src.models.student import Student
from src.models.presence_event import PresenceEvent as PresenceEventModel
from src.schemas.manual_session import SessionStartRequest
from src.schemas.presence_event import PresenceEvent as PresenceEventSchema
from src.schemas.event_types import EventType, TriggerSource
from src.schemas.identity import Role
from src.services.presence_engine import PresenceEngine
from src.services.session_manager import SessionManager
from src.services.manual_session_service import ManualSessionService
from src.services.runtime_recovery_service import RuntimeRecoveryService


class TestManualSessionAndRecovery(unittest.TestCase):
    def setUp(self):
        init_db()
        self.db = SessionLocal()
        
        # Clean previous sessions and events in correct FK dependency order
        from src.models.attendance import Attendance
        from src.models.student_presence_state import StudentPresenceState
        from src.models.authentication_log import AuthenticationLog
        from src.models.scan_log import ScanLog
        
        self.db.query(Attendance).delete()
        self.db.query(StudentPresenceState).delete()
        self.db.query(PresenceEventModel).delete()
        self.db.query(AuthenticationLog).delete()
        self.db.query(ScanLog).delete()
        self.db.query(ClassSession).delete()
        self.db.query(Faculty).delete()
        self.db.query(Student).delete()
        self.db.commit()

        # Seed Faculty and Student
        self.faculty_id = "FAC-01"
        self.fac = Faculty(id=self.faculty_id, name="Dr. Adheem", department="CSE")
        self.db.add(self.fac)
        
        self.student_id = "SET-12584"
        self.std = Student(id=self.student_id, name="Jane Student")
        self.db.add(self.std)
        self.db.commit()

        self.presence_engine = PresenceEngine()
        self.session_manager = SessionManager()
        self.manual_service = ManualSessionService(self.presence_engine, self.session_manager)
        self.recovery_service = RuntimeRecoveryService()

    def tearDown(self):
        self.db.close()

    def test_manual_start_and_end_session(self):
        req = SessionStartRequest(
            faculty_id=self.faculty_id,
            faculty_name="Dr. Adheem",
            subject="Algorithms",
            room="Room-101"
        )

        # 1. Start Session
        res = self.manual_service.start_session(req, self.db)
        self.db.commit()
        self.assertEqual(res["status"], "session_started")

        # Verify FACULTY_ENTER presence event was recorded
        events = self.db.query(PresenceEventModel).filter(PresenceEventModel.actor_id == self.faculty_id).all()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "FACULTY_ENTER")
        self.assertEqual(events[0].trigger_source, "MANUAL")

        # Verify active session subject was set from metadata
        active = self.session_manager.get_active_session(self.db)
        self.assertIsNotNone(active)
        self.assertEqual(active.subject, "Algorithms")
        self.assertEqual(active.room, "Room-101")

        # Verify faculty presence state was updated to INSIDE
        self.assertEqual(self.presence_engine.faculty_states[self.faculty_id]["presence_state"], "INSIDE")

        # 2. End Session
        res_end = self.manual_service.end_session(self.db)
        self.db.commit()
        self.assertEqual(res_end["status"], "session_ended")

        # Verify FACULTY_EXIT event was recorded
        events = self.db.query(PresenceEventModel).filter(PresenceEventModel.actor_id == self.faculty_id).all()
        self.assertEqual(len(events), 2)
        self.assertEqual(events[1].event_type, "FACULTY_EXIT")
        self.assertEqual(events[1].trigger_source, "MANUAL")

        # Verify faculty presence state was updated to OUTSIDE
        self.assertEqual(self.presence_engine.faculty_states[self.faculty_id]["presence_state"], "OUTSIDE")

    def test_runtime_recovery_replays_correctly(self):
        # 1. Simulate faculty ENTER event in the database
        event = PresenceEventSchema(
            event_type=EventType.FACULTY_ENTER,
            actor_id=self.faculty_id,
            actor_role=Role.FACULTY,
            classroom_id="Room-1",
            trigger_source=TriggerSource.SCANNER,
            timestamp=datetime.utcnow()
        )
        from src.repositories.presence_event_repo import PresenceEventRepository
        PresenceEventRepository(self.db).append(event)
        
        # Start the session matching this event
        self.db.add(ClassSession(
            faculty_name="Dr. Adheem",
            faculty_id=self.faculty_id,
            subject="Algorithms",
            slot="Hour 1",
            room="Room-1",
            started_at=datetime.utcnow().isoformat(),
            status="active"
        ))
        self.db.commit()

        # At this point, the presence_engine has NO in-memory state for self.faculty_id (since we just restarted)
        self.presence_engine.faculty_states.clear()

        # Run recovery
        report = self.recovery_service.recover_runtime(self.presence_engine, self.session_manager, self.db)
        self.assertEqual(report.faculty_recovered, 1)
        self.assertEqual(report.faculty_inside, 1)
        self.assertEqual(report.faculty_outside, 0)
        self.assertEqual(report.active_sessions, 1)
        self.assertEqual(report.ghost_sessions, 1)

        # Verify presence state has been recovered correctly
        self.assertEqual(self.presence_engine.faculty_states[self.faculty_id]["presence_state"], "INSIDE")


if __name__ == "__main__":
    unittest.main()
