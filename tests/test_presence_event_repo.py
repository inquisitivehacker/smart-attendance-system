import tests.test_env  # noqa: F401
import unittest
import json
from datetime import datetime
from src.database import init_db, SessionLocal
from src.schemas.presence_event import PresenceEvent as PresenceEventSchema
from src.schemas.event_types import EventType, TriggerSource
from src.schemas.identity import Role
from src.repositories.presence_event_repo import PresenceEventRepository
from src.models.presence_event import PresenceEvent as PresenceEventModel


class TestPresenceEventRepository(unittest.TestCase):
    def setUp(self):
        init_db()
        self.db = SessionLocal()
        self.repo = PresenceEventRepository(self.db)

        # Clean previous test entries
        self.db.query(PresenceEventModel).filter(
            PresenceEventModel.actor_id == "TEST-ACTOR-123"
        ).delete()
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_append_event_and_serialization(self):
        now = datetime.utcnow()
        schema = PresenceEventSchema(
            event_type=EventType.STUDENT_ENTER,
            actor_id="TEST-ACTOR-123",
            actor_role=Role.STUDENT,
            classroom_id="Room-1",
            trigger_source=TriggerSource.SCANNER,
            metadata={"face_confidence": 0.96},
            timestamp=now
        )

        # 1. Append
        model = self.repo.append(schema)
        self.db.commit()

        self.assertIsNotNone(model.event_id)
        self.assertEqual(model.actor_id, "TEST-ACTOR-123")
        self.assertEqual(model.event_type, "STUDENT_ENTER")

        # 2. Check DB directly for serialization format
        db_model = self.db.query(PresenceEventModel).filter(
            PresenceEventModel.event_id == model.event_id
        ).first()
        self.assertIsNotNone(db_model)

        # Check metadata JSON string serialization
        meta = json.loads(db_model.event_metadata)
        self.assertEqual(meta["face_confidence"], 0.96)

    def test_ledger_append_only_methods(self):
        # Verify that forbidden methods do not exist
        for forbidden in ["update", "delete", "replace", "merge", "upsert", "save"]:
            self.assertFalse(hasattr(self.repo, forbidden), f"Forbidden method '{forbidden}' exists on repository!")


if __name__ == "__main__":
    unittest.main()
