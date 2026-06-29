import unittest
from datetime import datetime, timedelta
from src.schemas.identity import AuthenticationResult, Identity, Role, AuthenticationStatus
from src.schemas.event_types import EventType
from src.schemas.event_context import EventContext
from src.services.event_resolver import EventResolver


class TestEventResolver(unittest.TestCase):
    def setUp(self):
        self.resolver = EventResolver()

    def test_student_outside_to_enter(self):
        auth = AuthenticationResult(
            authenticated=True,
            rejection_reason=AuthenticationStatus.SUCCESS,
            confidence=1.0,
            identity=Identity(id="SET-12584", name="Sanjaynath", role=Role.STUDENT)
        )
        context = EventContext(
            auth_result=auth,
            student_presence_state="OUTSIDE",
            current_time=datetime.utcnow()
        )
        event = self.resolver.resolve_event(context)
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, EventType.STUDENT_ENTER)
        self.assertEqual(event.actor_id, "SET-12584")
        self.assertEqual(event.actor_role, Role.STUDENT)

    def test_student_inside_to_exit(self):
        auth = AuthenticationResult(
            authenticated=True,
            rejection_reason=AuthenticationStatus.SUCCESS,
            confidence=1.0,
            identity=Identity(id="SET-12584", name="Sanjaynath", role=Role.STUDENT)
        )
        context = EventContext(
            auth_result=auth,
            student_presence_state="INSIDE",
            current_time=datetime.utcnow()
        )
        event = self.resolver.resolve_event(context)
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, EventType.STUDENT_EXIT)
        self.assertEqual(event.actor_id, "SET-12584")

    def test_student_stale_to_enter(self):
        auth = AuthenticationResult(
            authenticated=True,
            rejection_reason=AuthenticationStatus.SUCCESS,
            confidence=0.9,
            identity=Identity(id="SET-12584", name="Sanjaynath", role=Role.STUDENT)
        )
        context = EventContext(
            auth_result=auth,
            student_presence_state="STALE",
            current_time=datetime.utcnow()
        )
        event = self.resolver.resolve_event(context)
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, EventType.STUDENT_ENTER)
        self.assertTrue(event.metadata.get("stale_reconciliation"))

    def test_faculty_outside_to_enter(self):
        auth = AuthenticationResult(
            authenticated=True,
            rejection_reason=AuthenticationStatus.SUCCESS,
            confidence=1.0,
            identity=Identity(id="FAC-01", name="Dr. Adheem", role=Role.FACULTY)
        )
        context = EventContext(
            auth_result=auth,
            faculty_presence_state="OUTSIDE",
            current_time=datetime.utcnow()
        )
        event = self.resolver.resolve_event(context)
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, EventType.FACULTY_ENTER)
        self.assertEqual(event.actor_id, "FAC-01")

    def test_faculty_inside_to_exit(self):
        auth = AuthenticationResult(
            authenticated=True,
            rejection_reason=AuthenticationStatus.SUCCESS,
            confidence=1.0,
            identity=Identity(id="FAC-01", name="Dr. Adheem", role=Role.FACULTY)
        )
        context = EventContext(
            auth_result=auth,
            faculty_presence_state="INSIDE",
            current_time=datetime.utcnow()
        )
        event = self.resolver.resolve_event(context)
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, EventType.FACULTY_EXIT)
        self.assertEqual(event.actor_id, "FAC-01")

    def test_cooldown_duplicate_resolves_to_none(self):
        auth = AuthenticationResult(
            authenticated=True,
            rejection_reason=AuthenticationStatus.SUCCESS,
            confidence=1.0,
            identity=Identity(id="SET-12584", name="Sanjaynath", role=Role.STUDENT)
        )
        now = datetime.utcnow()
        context = EventContext(
            auth_result=auth,
            student_presence_state="INSIDE",
            last_scan_timestamp=now - timedelta(seconds=10),
            current_time=now
        )
        event = self.resolver.resolve_event(context)
        self.assertIsNone(event)

    def test_auth_failure_resolves_to_none(self):
        auth = AuthenticationResult(
            authenticated=False,
            rejection_reason=AuthenticationStatus.REJECTED_FACE,
            confidence=0.1,
            identity=None
        )
        context = EventContext(
            auth_result=auth,
            current_time=datetime.utcnow()
        )
        event = self.resolver.resolve_event(context)
        self.assertIsNone(event)


if __name__ == "__main__":
    unittest.main()
