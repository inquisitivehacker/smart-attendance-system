import json
import logging
from sqlalchemy.orm import Session as DBSession
from src.models.presence_event import PresenceEvent as PresenceEventModel
from src.schemas.presence_event import PresenceEvent as PresenceEventSchema

logger = logging.getLogger(__name__)


class PresenceEventRepository:
    """
    Append-only repository for the presence_events database table.
    Enforces a strict immutable event ledger design pattern.
    
    FORBIDDEN OPERATIONS (Violates ledger purity):
    - NO update()
    - NO delete()
    - NO replace()
    - NO merge()
    - NO upsert()
    - NO save()
    """

    def __init__(self, db: DBSession):
        self.db = db

    def append(self, schema: PresenceEventSchema) -> PresenceEventModel:
        """
        Serializes and appends an immutable PresenceEvent to the event store.
        Does NOT commit the transaction (caller controls transaction boundaries).
        """
        metadata_str = json.dumps(schema.metadata) if schema.metadata is not None else None
        
        model = PresenceEventModel(
            event_version=schema.event_version,
            event_type=schema.event_type.value,
            actor_id=schema.actor_id,
            actor_role=schema.actor_role.value,
            classroom_id=schema.classroom_id,
            trigger_source=schema.trigger_source.value,
            event_metadata=metadata_str,
            timestamp=schema.timestamp
        )
        self.db.add(model)
        return model

    def get(self, event_id: int) -> PresenceEventModel | None:
        """Retrieve a single event by its ID."""
        return self.db.query(PresenceEventModel).filter(PresenceEventModel.event_id == event_id).first()

    def find(self, actor_id: str) -> list[PresenceEventModel]:
        """Find all presence events associated with a specific actor ID."""
        return (
            self.db.query(PresenceEventModel)
            .filter(PresenceEventModel.actor_id == actor_id)
            .order_by(PresenceEventModel.timestamp.asc())
            .all()
        )

    def list(self, limit: int = 100) -> list[PresenceEventModel]:
        """List the most recent events up to a limit."""
        return (
            self.db.query(PresenceEventModel)
            .order_by(PresenceEventModel.timestamp.desc())
            .limit(limit)
            .all()
        )
