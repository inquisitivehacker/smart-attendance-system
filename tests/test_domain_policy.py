import tests.test_env  # noqa: F401
import unittest
from datetime import datetime, timedelta

from src.schemas.event_types import EventType, TriggerSource
from src.schemas.presence_event import PresenceEvent
from src.schemas.identity import Role
from src.schemas.attendance_policy import (
    PresenceInterval,
    InstitutionPolicy,
    PolicyContext,
    ParticipationMetrics,
    AttendanceDecision,
)
from src.services.interval_builder import IntervalBuilder
from src.services.participation_evaluator import ParticipationEvaluator
from src.services.policy_engine import PolicyEngine
from src.services.attendance_assembler import AttendanceAssembler


class TestDomainPolicyPipeline(unittest.TestCase):

    # --- IntervalBuilder Tests ---

    def test_interval_builder_normal_and_duplicates(self):
        t1 = datetime(2026, 7, 2, 9, 0, 0)
        t2 = datetime(2026, 7, 2, 9, 15, 0)
        t3 = datetime(2026, 7, 2, 9, 30, 0)
        t4 = datetime(2026, 7, 2, 9, 45, 0)

        events = [
            PresenceEvent(
                event_type=EventType.STUDENT_ENTER,
                actor_id="ST-01",
                actor_role=Role.STUDENT,
                timestamp=t1,
                trigger_source=TriggerSource.SCANNER
            ),
            PresenceEvent(
                event_type=EventType.STUDENT_ENTER,  # Duplicate enter - should ignore
                actor_id="ST-01",
                actor_role=Role.STUDENT,
                timestamp=t1 + timedelta(seconds=1),
                trigger_source=TriggerSource.SCANNER
            ),
            PresenceEvent(
                event_type=EventType.STUDENT_EXIT,
                actor_id="ST-01",
                actor_role=Role.STUDENT,
                timestamp=t2,
                trigger_source=TriggerSource.SCANNER
            ),
            PresenceEvent(
                event_type=EventType.STUDENT_EXIT,  # Duplicate exit - should ignore
                actor_id="ST-01",
                actor_role=Role.STUDENT,
                timestamp=t2 + timedelta(seconds=1),
                trigger_source=TriggerSource.SCANNER
            ),
            PresenceEvent(
                event_type=EventType.STUDENT_ENTER,
                actor_id="ST-01",
                actor_role=Role.STUDENT,
                timestamp=t3,
                trigger_source=TriggerSource.SCANNER
            ),
            PresenceEvent(
                event_type=EventType.STUDENT_EXIT,
                actor_id="ST-01",
                actor_role=Role.STUDENT,
                timestamp=t4,
                trigger_source=TriggerSource.SCANNER
            ),
        ]

        intervals = IntervalBuilder.build_intervals(events)
        self.assertEqual(len(intervals), 2)
        self.assertEqual(intervals[0].enter_time, t1)
        self.assertEqual(intervals[0].exit_time, t2)
        self.assertEqual(intervals[1].enter_time, t3)
        self.assertEqual(intervals[1].exit_time, t4)

    def test_interval_builder_open_interval_and_out_of_order(self):
        t1 = datetime(2026, 7, 2, 9, 0, 0)
        t2 = datetime(2026, 7, 2, 9, 30, 0)

        # EXIT occurs before ENTER in out-of-order logs, but sorting resolves it
        events = [
            PresenceEvent(
                event_type=EventType.STUDENT_ENTER,
                actor_id="ST-01",
                actor_role=Role.STUDENT,
                timestamp=t1,
                trigger_source=TriggerSource.SCANNER
            ),
            PresenceEvent(
                event_type=EventType.STUDENT_EXIT,
                actor_id="ST-01",
                actor_role=Role.STUDENT,
                timestamp=t2,
                trigger_source=TriggerSource.SCANNER
            ),
            PresenceEvent(
                event_type=EventType.STUDENT_ENTER,  # Open interval at end
                actor_id="ST-01",
                actor_role=Role.STUDENT,
                timestamp=t2 + timedelta(hours=1),
                trigger_source=TriggerSource.SCANNER
            ),
        ]

        # Reverse the order to test sorting
        events.reverse()

        intervals = IntervalBuilder.build_intervals(events)
        self.assertEqual(len(intervals), 2)
        self.assertEqual(intervals[0].enter_time, t1)
        self.assertEqual(intervals[0].exit_time, t2)
        self.assertEqual(intervals[1].enter_time, t2 + timedelta(hours=1))
        self.assertIsNone(intervals[1].exit_time)

    # --- ParticipationEvaluator Tests ---

    def test_participation_evaluator_clipping_and_math(self):
        session_start = datetime(2026, 7, 2, 9, 0, 0)
        session_end = datetime(2026, 7, 2, 10, 0, 0)  # 60 minutes session (3600 seconds)

        intervals = [
            # 1. Early entry, exit inside class: clipped to start at 09:00
            PresenceInterval(
                enter_time=datetime(2026, 7, 2, 8, 55, 0),
                exit_time=datetime(2026, 7, 2, 9, 15, 0)  # 15 minutes present inside (900 seconds)
            ),
            # 2. Entry inside, exit after class end: clipped to end at 10:00
            PresenceInterval(
                enter_time=datetime(2026, 7, 2, 9, 45, 0),
                exit_time=datetime(2026, 7, 2, 10, 15, 0)  # 15 minutes present inside (900 seconds)
            ),
            # 3. Completely outside after session end: clipped to 0 participation
            PresenceInterval(
                enter_time=datetime(2026, 7, 2, 10, 20, 0),
                exit_time=datetime(2026, 7, 2, 10, 30, 0)
            )
        ]

        metrics = ParticipationEvaluator.evaluate(intervals, session_start, session_end)

        self.assertEqual(metrics.participation_seconds, 1800)  # 900 + 900 = 1800s (30 minutes)
        self.assertEqual(metrics.participation_percentage, 50.0)
        self.assertEqual(metrics.late_minutes, 0)  # Entered early (before 09:00)
        self.assertEqual(metrics.early_departure_minutes, 0)  # Left after 10:00 (exit clipped to 10:00)
        self.assertEqual(metrics.entries, 3)
        self.assertEqual(metrics.exits, 3)
        self.assertTrue(metrics.entered_before_session)
        self.assertTrue(metrics.inside_at_session_end)

    def test_participation_evaluator_late_and_early_exit(self):
        session_start = datetime(2026, 7, 2, 9, 0, 0)
        session_end = datetime(2026, 7, 2, 10, 0, 0)

        intervals = [
            PresenceInterval(
                enter_time=datetime(2026, 7, 2, 9, 15, 0),  # 15 minutes late
                exit_time=datetime(2026, 7, 2, 9, 45, 0)  # Left 15 minutes early
            )
        ]

        metrics = ParticipationEvaluator.evaluate(intervals, session_start, session_end)
        self.assertEqual(metrics.participation_seconds, 1800)
        self.assertEqual(metrics.late_minutes, 15)
        self.assertEqual(metrics.early_departure_minutes, 15)
        self.assertFalse(metrics.entered_before_session)
        self.assertFalse(metrics.inside_at_session_end)

    # --- PolicyEngine Tests ---

    def test_policy_engine_decisions(self):
        policy = InstitutionPolicy(
            policy_id="POL-01",
            version="1.0",
            effective_from=datetime.utcnow(),
            minimum_attendance_percentage=75.0,
            late_grace_minutes=10,
            early_exit_grace_minutes=10,
            regularization_threshold=50.0
        )

        session_start = datetime(2026, 7, 2, 9, 0, 0)
        session_end = datetime(2026, 7, 2, 10, 0, 0)

        # Scenario 1: Met all requirements (PRESENT)
        m1 = ParticipationMetrics(
            participation_seconds=2800,
            participation_percentage=77.78,
            late_minutes=5,
            early_departure_minutes=5,
            entries=1,
            exits=1,
            entered_before_session=False,
            inside_at_session_end=True
        )
        c1 = PolicyContext(
            student_id="ST-01",
            session_id=1,
            session_start=session_start,
            session_end=session_end,
            metrics=m1,
            policy=policy
        )
        d1 = PolicyEngine.evaluate(c1)
        self.assertEqual(d1.status, "PRESENT")
        self.assertTrue(d1.present)
        self.assertFalse(d1.regularization_required)

        # Scenario 2: Exceeded grace period but above floor (REGULARIZATION)
        m2 = ParticipationMetrics(
            participation_seconds=2700,
            participation_percentage=75.0,
            late_minutes=15,  # Exceeds 10m grace period
            early_departure_minutes=0,
            entries=1,
            exits=1,
            entered_before_session=False,
            inside_at_session_end=True
        )
        c2 = PolicyContext(
            student_id="ST-01",
            session_id=1,
            session_start=session_start,
            session_end=session_end,
            metrics=m2,
            policy=policy
        )
        d2 = PolicyEngine.evaluate(c2)
        self.assertEqual(d2.status, "REGULARIZATION")
        self.assertFalse(d2.present)
        self.assertTrue(d2.regularization_required)

        # Scenario 3: Below regularization floor (ABSENT)
        m3 = ParticipationMetrics(
            participation_seconds=1000,
            participation_percentage=27.78,  # Below 50.0 threshold
            late_minutes=0,
            early_departure_minutes=0,
            entries=1,
            exits=1,
            entered_before_session=True,
            inside_at_session_end=False
        )
        c3 = PolicyContext(
            student_id="ST-01",
            session_id=1,
            session_start=session_start,
            session_end=session_end,
            metrics=m3,
            policy=policy
        )
        d3 = PolicyEngine.evaluate(c3)
        self.assertEqual(d3.status, "ABSENT")
        self.assertFalse(d3.present)
        self.assertFalse(d3.regularization_required)

    # --- AttendanceAssembler Tests ---

    def test_attendance_assembler_mapping(self):
        m = ParticipationMetrics(
            participation_seconds=2700,
            participation_percentage=75.0,
            late_minutes=15,
            early_departure_minutes=0,
            entries=1,
            exits=1,
            entered_before_session=False,
            inside_at_session_end=True
        )
        d = AttendanceDecision(
            status="REGULARIZATION",
            present=False,
            regularization_required=True,
            reason="exceeded_late_grace_period",
            policy_id="POL-01",
            policy_version="1.0"
        )

        record = AttendanceAssembler.assemble(
            student_id="ST-01",
            session_id=10,
            metrics=m,
            decision=d
        )

        self.assertEqual(record.student_id, "ST-01")
        self.assertEqual(record.session_id, 10)
        self.assertEqual(record.status, "REGULARIZATION")
        self.assertEqual(record.policy_version, "1.0")
        self.assertEqual(record.participation_seconds, 2700)
        self.assertEqual(record.participation_percentage, 75.0)


if __name__ == "__main__":
    unittest.main()
