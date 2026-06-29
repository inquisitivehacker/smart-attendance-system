import unittest
from datetime import datetime, timedelta
from src.schemas.event_types import EventType
from src.services.presence_state_machine import PresenceStateMachine


class TestPresenceStateMachine(unittest.TestCase):
    def setUp(self):
        self.machine = PresenceStateMachine()

    def test_outside_to_inside(self):
        now = datetime.utcnow()
        state, health, since, acc = self.machine.transition(
            current_state="OUTSIDE",
            current_health="NORMAL",
            inside_since=None,
            accumulated_seconds=0,
            event_type=EventType.STUDENT_ENTER,
            current_time=now
        )
        self.assertEqual(state, "INSIDE")
        self.assertEqual(health, "NORMAL")
        self.assertEqual(since, now)
        self.assertEqual(acc, 0)

    def test_inside_to_outside_duration_accumulation(self):
        now = datetime.utcnow()
        start = now - timedelta(seconds=100)
        state, health, since, acc = self.machine.transition(
            current_state="INSIDE",
            current_health="NORMAL",
            inside_since=start,
            accumulated_seconds=50,
            event_type=EventType.STUDENT_EXIT,
            current_time=now
        )
        self.assertEqual(state, "OUTSIDE")
        self.assertEqual(health, "NORMAL")
        self.assertIsNone(since)
        self.assertEqual(acc, 150)  # 50 + 100

    def test_stale_to_inside_reconciliation(self):
        now = datetime.utcnow()
        start = now - timedelta(hours=15)
        state, health, since, acc = self.machine.transition(
            current_state="INSIDE",
            current_health="STALE",
            inside_since=start,
            accumulated_seconds=10,
            event_type=EventType.STUDENT_ENTER,
            current_time=now
        )
        self.assertEqual(state, "INSIDE")
        self.assertEqual(health, "NORMAL")
        self.assertEqual(since, now)
        self.assertEqual(acc, 10)  # No duration accumulated for stale window

    def test_invalid_transitions_protection(self):
        # E.g. Enter when already INSIDE: should not change inside_since or reset state
        now = datetime.utcnow()
        start = now - timedelta(seconds=200)
        state, health, since, acc = self.machine.transition(
            current_state="INSIDE",
            current_health="NORMAL",
            inside_since=start,
            accumulated_seconds=0,
            event_type=EventType.STUDENT_ENTER,
            current_time=now
        )
        self.assertEqual(state, "INSIDE")
        self.assertEqual(health, "NORMAL")
        self.assertEqual(since, start)  # Retained old entry timestamp
        self.assertEqual(acc, 0)

    def test_exit_when_outside(self):
        # Exit when already OUTSIDE: should not change state or accumulate seconds
        now = datetime.utcnow()
        state, health, since, acc = self.machine.transition(
            current_state="OUTSIDE",
            current_health="NORMAL",
            inside_since=None,
            accumulated_seconds=10,
            event_type=EventType.STUDENT_EXIT,
            current_time=now
        )
        self.assertEqual(state, "OUTSIDE")
        self.assertEqual(health, "NORMAL")
        self.assertIsNone(since)
        self.assertEqual(acc, 10)


if __name__ == "__main__":
    unittest.main()
