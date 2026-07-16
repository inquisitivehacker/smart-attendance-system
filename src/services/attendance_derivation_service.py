import logging
from datetime import datetime
from sqlalchemy.orm import Session as DBSession

from src.models.session import Session as ClassSession
from src.models.student import Student
from src.models.presence_event import PresenceEvent as PresenceEventModel
from src.schemas.attendance_policy import InstitutionPolicy, PolicyContext, AttendanceRecord
from src.repositories.attendance_repo import AttendanceRepository
from src.services.interval_builder import IntervalBuilder
from src.services.participation_evaluator import ParticipationEvaluator
from src.services.policy_engine import PolicyEngine
from src.services.attendance_assembler import AttendanceAssembler

logger = logging.getLogger(__name__)


class AttendanceDerivationService:
    """
    Application orchestrator responsible for compiling raw physical occupancy history
    into derived academic attendance records. Handles database transaction boundaries.
    """

    def __init__(self, policy: InstitutionPolicy = None):
        # Default fallback policy configuration (Phase 6 abstraction priority)
        self.policy = policy or InstitutionPolicy(
            policy_id="POL-01",
            version="1.0",
            effective_from=datetime.min,
            minimum_attendance_percentage=75.0,
            late_grace_minutes=10,
            early_exit_grace_minutes=10,
            regularization_threshold=50.0
        )

    def derive_session_attendance(self, session_id: int, db: DBSession) -> list[AttendanceRecord]:
        """
        Derives and commits attendance records for all active students for a given session.
        Executes within a single transaction scope (All-or-Nothing).
        """
        # 1. Load session details
        session_record = db.query(ClassSession).filter(ClassSession.id == session_id).first()
        if not session_record:
            raise ValueError(f"Session with ID {session_id} not found.")

        session_start = datetime.fromisoformat(session_record.started_at)
        session_end = (
            datetime.fromisoformat(session_record.ended_at)
            if session_record.ended_at
            else datetime.utcnow()
        )

        # 2. Open batch derivation transaction block
        try:
            # Load all registered students
            student_ids = [row[0] for row in db.query(Student.id).all()]
            
            # Load and group student PresenceEvents scoped to session time window only.
            from src.repositories.presence_event_repo import PresenceEventRepository
            event_repo = PresenceEventRepository(db)
            event_records = event_repo.find_student_events_for_session(
                session_start=session_start,
                session_end=session_end
            )
            
            from collections import defaultdict
            student_events = defaultdict(list)
            for event in event_records:
                student_events[event.actor_id].append(event)

            attendance_repo = AttendanceRepository(db)
            records = []

            # 3. Derive attendance for each student
            for student_id in student_ids:
                events_for_student = student_events[student_id]

                # Pipeline Step A: Reconstruct physical occupancy intervals
                intervals = IntervalBuilder.build_intervals(events_for_student)

                # Pipeline Step B: Evaluate factual participation metrics
                metrics = ParticipationEvaluator.evaluate(intervals, session_start, session_end)

                # Pipeline Step C: Resolve institutional grading decision
                context = PolicyContext(
                    student_id=student_id,
                    session_id=session_id,
                    session_start=session_start,
                    session_end=session_end,
                    metrics=metrics,
                    policy=self.policy
                )
                decision = PolicyEngine.evaluate(context)

                # Pipeline Step D: Assemble relational persistence projection
                record = AttendanceAssembler.assemble(student_id, session_id, metrics, decision)

                # Pipeline Step E: Save to database (no commit yet!)
                attendance_repo.upsert_attendance(record)
                records.append(record)

            # Commit all evaluations atomically
            db.commit()
            logger.info(f"Attendance successfully derived for session {session_id} ({len(records)} students).")
            return records

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to derive attendance for session {session_id}, changes rolled back: {e}")
            raise e
