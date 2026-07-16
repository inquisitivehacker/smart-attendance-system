import tests.test_env  # noqa: F401
import unittest
from datetime import datetime, timedelta

from src.database import init_db, SessionLocal
from src.models.session import Session as ClassSession
from src.models.student import Student
from src.models.faculty import Faculty
from src.models.attendance import Attendance
from src.models.presence_event import PresenceEvent as PresenceEventModel
from src.schemas.event_types import EventType, TriggerSource
from src.services.attendance_derivation_service import AttendanceDerivationService
from src.repositories.presence_event_repo import PresenceEventRepository
from src.schemas.presence_event import PresenceEvent as PresenceEventSchema
from src.schemas.identity import Role


class TestAttendanceDerivation(unittest.TestCase):
    def setUp(self):
        init_db()
        self.db = SessionLocal()

        # Clean previous session and events in correct FK dependency order
        self.db.query(Attendance).delete()
        self.db.query(PresenceEventModel).delete()
        self.db.query(ClassSession).filter(ClassSession.subject == "Computer Science").delete()
        self.db.commit()

        # Seed student SET-12584 if missing
        self.student_id = "SET-12584"
        std = self.db.query(Student).filter(Student.id == self.student_id).first()
        if not std:
            std = Student(id=self.student_id, name="Jane Student")
            self.db.add(std)
            self.db.commit()

        # Seed Faculty FAC-01 if missing
        self.faculty_id = "FAC-01"
        fac = self.db.query(Faculty).filter(Faculty.id == self.faculty_id).first()
        if not fac:
            fac = Faculty(id=self.faculty_id, name="Dr. Adheem", department="CSE")
            self.db.add(fac)
            self.db.commit()

        # Create a completed test session
        self.session_start = datetime.utcnow() - timedelta(hours=1)
        self.session_end = datetime.utcnow()
        self.session = ClassSession(
            faculty_name="Dr. Adheem",
            faculty_id=self.faculty_id,
            subject="Computer Science",
            slot="Hour 1",
            started_at=self.session_start.isoformat(),
            ended_at=self.session_end.isoformat(),
            status="completed"
        )
        self.db.add(self.session)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_complete_derivation_and_idempotency(self):
        # 1. Seed events for student
        event_repo = PresenceEventRepository(self.db)

        # Enter 5 minutes before class starts (clipped to session start)
        t_enter = self.session_start - timedelta(minutes=5)
        # Exit 30 minutes after start (30 minutes / 1800s participation)
        t_exit = self.session_start + timedelta(minutes=30)

        event_repo.append(PresenceEventSchema(
            event_type=EventType.STUDENT_ENTER,
            actor_id=self.student_id,
            actor_role=Role.STUDENT,
            classroom_id="Room-1",
            trigger_source=TriggerSource.SCANNER,
            timestamp=t_enter
        ))
        event_repo.append(PresenceEventSchema(
            event_type=EventType.STUDENT_EXIT,
            actor_id=self.student_id,
            actor_role=Role.STUDENT,
            classroom_id="Room-1",
            trigger_source=TriggerSource.SCANNER,
            timestamp=t_exit
        ))
        self.db.commit()

        # 2. Derive attendance
        svc = AttendanceDerivationService()
        records = svc.derive_session_attendance(self.session.id, self.db)

        # Check generated records
        student_records = [r for r in records if r.student_id == self.student_id]
        self.assertEqual(len(student_records), 1)
        # 30 mins present out of 60 mins session = 50.0% participation percentage.
        # Fits criteria for REGULARIZATION (above 50.0% floor, below 75.0% minimum)
        self.assertEqual(student_records[0].status, "REGULARIZATION")
        self.assertEqual(student_records[0].participation_seconds, 1800)

        # Check DB directly
        db_attendance = self.db.query(Attendance).filter(
            Attendance.student_id == self.student_id,
            Attendance.session_id == self.session.id
        ).first()
        self.assertIsNotNone(db_attendance)
        self.assertEqual(db_attendance.status, "REGULARIZATION")
        self.assertEqual(db_attendance.duration_seconds, 1800)

        # 3. Test Idempotency: Run again and verify no duplicate record is created
        svc.derive_session_attendance(self.session.id, self.db)
        total_records = self.db.query(Attendance).filter(
            Attendance.student_id == self.student_id,
            Attendance.session_id == self.session.id
        ).all()
        self.assertEqual(len(total_records), 1)

    def test_derivation_rollback_on_failure(self):
        # Create derivation service
        svc = AttendanceDerivationService()

        # Artificially simulate database failure by querying mock
        original_query = self.db.query

        def failing_query(*args, **kwargs):
            raise Exception("Mock Database Failure")
        self.db.query = failing_query

        with self.assertRaises(Exception) as context:
            svc.derive_session_attendance(self.session.id, self.db)
        self.assertIn("Mock Database Failure", str(context.exception))

        # Restore query
        self.db.query = original_query

        # Check DB: no attendance record should be written
        total_records = self.db.query(Attendance).all()
        self.assertEqual(len(total_records), 0)


if __name__ == "__main__":
    unittest.main()
