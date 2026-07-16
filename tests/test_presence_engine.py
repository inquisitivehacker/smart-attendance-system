import tests.test_env  # noqa: F401
import unittest
from datetime import datetime
from src.database import init_db, SessionLocal
from src.schemas.presence_event import PresenceEvent
from src.schemas.event_types import EventType, TriggerSource
from src.schemas.identity import Role
from src.services.presence_engine import PresenceEngine
from src.models.student_presence_state import StudentPresenceState


class TestPresenceEngineIntegration(unittest.TestCase):
    def setUp(self):
        init_db()
        self.db = SessionLocal()
        self.engine = PresenceEngine()

        # Clean previous presence data for test student
        self.student_id = "SET-12584"
        
        # Seed student if missing (required for foreign key referential integrity)
        from src.models.student import Student
        std = self.db.query(Student).filter(Student.id == self.student_id).first()
        if not std:
            std = Student(id=self.student_id, name="Jane Student")
            self.db.add(std)
            self.db.commit()

        record = self.db.query(StudentPresenceState).filter(
            StudentPresenceState.student_id == self.student_id
        ).first()
        if record:
            self.db.delete(record)
            self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_engine_student_occupancy_db_pipeline(self):
        now = datetime.utcnow()
        event = PresenceEvent(
            event_type=EventType.STUDENT_ENTER,
            actor_id=self.student_id,
            actor_role=Role.STUDENT,
            trigger_source=TriggerSource.SCANNER,
            timestamp=now
        )

        # 1. Process entry
        res = self.engine.process_event(event, self.db)
        self.db.commit()  # Save changes

        # Check returned dict
        self.assertEqual(res["presence_state"], "INSIDE")
        self.assertEqual(res["presence_health"], "NORMAL")

        # Check DB directly
        db_state = self.db.query(StudentPresenceState).filter(
            StudentPresenceState.student_id == self.student_id
        ).first()
        self.assertIsNotNone(db_state)
        self.assertEqual(db_state.presence_state, "INSIDE")
        self.assertEqual(db_state.presence_health, "NORMAL")

        # 2. Process exit
        exit_event = PresenceEvent(
            event_type=EventType.STUDENT_EXIT,
            actor_id=self.student_id,
            actor_role=Role.STUDENT,
            trigger_source=TriggerSource.SCANNER,
            timestamp=datetime.utcnow()
        )
        res_exit = self.engine.process_event(exit_event, self.db)
        self.db.commit()

        self.assertEqual(res_exit["presence_state"], "OUTSIDE")

        db_state_exit = self.db.query(StudentPresenceState).filter(
            StudentPresenceState.student_id == self.student_id
        ).first()
        self.assertEqual(db_state_exit.presence_state, "OUTSIDE")


if __name__ == "__main__":
    unittest.main()
