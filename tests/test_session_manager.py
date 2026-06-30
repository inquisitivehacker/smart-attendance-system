import unittest
from datetime import datetime
from unittest.mock import MagicMock
from sqlalchemy.orm import Session as DBSession

from src.database import init_db, SessionLocal
from src.schemas.presence_event import PresenceEvent
from src.schemas.event_types import EventType, TriggerSource
from src.schemas.identity import Role
from src.services.session_manager import SessionManager
from src.models.session import Session as ClassSession
from src.models.faculty import Faculty


class TestSessionManager(unittest.TestCase):
    def setUp(self):
        init_db()
        self.db = SessionLocal()
        self.manager = SessionManager()

        # Seed a test faculty if missing
        self.faculty_id = "FAC-01"
        fac = self.db.query(Faculty).filter(Faculty.id == self.faculty_id).first()
        if not fac:
            fac = Faculty(id=self.faculty_id, name="Test Faculty", department="CSE", email="cse@test.com")
            self.db.add(fac)
            self.db.commit()

        # Clean active sessions
        self.db.query(ClassSession).filter(ClassSession.status == "active").delete()
        self.db.commit()

    def tearDown(self):
        self.db.query(ClassSession).filter(ClassSession.status == "active").delete()
        self.db.commit()
        self.db.close()

    def test_faculty_enter_starts_session(self):
        event = PresenceEvent(
            event_type=EventType.FACULTY_ENTER,
            actor_id=self.faculty_id,
            actor_role=Role.FACULTY,
            classroom_id="Room-1",
            trigger_source=TriggerSource.SCANNER,
            timestamp=datetime.utcnow()
        )

        # Handle event (no commit inside handle_event)
        res = self.manager.handle_event(event, self.db)
        self.assertEqual(res["status"], "session_started")
        
        # Verify the session is added to session, but not committed to DB yet
        fac = self.db.query(Faculty).filter(Faculty.id == self.faculty_id).first()
        active = self.db.query(ClassSession).filter(ClassSession.status == "active").first()
        self.assertIsNotNone(active)
        self.assertEqual(active.faculty_name, fac.name)
        self.assertEqual(active.faculty_id, self.faculty_id)


    def test_faculty_exit_ends_session(self):
        # 1. Start a session
        session = ClassSession(
            faculty_name="Test Faculty",
            faculty_id=self.faculty_id,
            subject="Computer Science",
            slot="Hour 1",
            room="Room-1",
            started_at=datetime.utcnow().isoformat(),
            status="active"
        )
        self.db.add(session)
        self.db.commit()

        event = PresenceEvent(
            event_type=EventType.FACULTY_EXIT,
            actor_id=self.faculty_id,
            actor_role=Role.FACULTY,
            classroom_id="Room-1",
            trigger_source=TriggerSource.SCANNER,
            timestamp=datetime.utcnow()
        )

        res = self.manager.handle_event(event, self.db)
        self.assertEqual(res["status"], "session_ended")

        # Verify state is updated to completed
        updated = self.db.query(ClassSession).filter(ClassSession.id == session.id).first()
        self.assertEqual(updated.status, "completed")
        self.assertIsNotNone(updated.ended_at)

    def test_student_events_ignored(self):
        event = PresenceEvent(
            event_type=EventType.STUDENT_ENTER,
            actor_id="SET-12584",
            actor_role=Role.STUDENT,
            classroom_id="Room-1",
            trigger_source=TriggerSource.SCANNER,
            timestamp=datetime.utcnow()
        )
        res = self.manager.handle_event(event, self.db)
        self.assertIsNone(res)

    def test_session_manager_never_commits(self):
        # Mock SessionLocal and check that commit is never called
        mock_db = MagicMock(spec=DBSession)
        # Setup mock active check
        mock_db.query().filter().first.return_value = None
        
        event = PresenceEvent(
            event_type=EventType.FACULTY_ENTER,
            actor_id=self.faculty_id,
            actor_role=Role.FACULTY,
            classroom_id="Room-1",
            trigger_source=TriggerSource.SCANNER,
            timestamp=datetime.utcnow()
        )
        self.manager.handle_event(event, mock_db)
        
        # Verify commit was never invoked on the session
        mock_db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
