import logging
from src.config import settings
from src.schemas.event_types import EventType, TriggerSource
from src.schemas.event_context import EventContext
from src.schemas.presence_event import PresenceEvent
from src.schemas.identity import Role

logger = logging.getLogger(__name__)


class EventResolver:
    """
    Pure decision engine that determines which physical classroom presence
    event occurred based on authentication results and current runtime state.
    """

    def resolve_event(self, context: EventContext) -> PresenceEvent | None:
        # 1. Rule 3: Authentication failures return None (no classroom state changed)
        if not context.auth_result.authenticated or not context.auth_result.identity:
            return None

        identity = context.auth_result.identity

        # 2. Duplicate scan check (cooldown validation)
        if context.last_scan_timestamp:
            delta = (context.current_time - context.last_scan_timestamp).total_seconds()
            if delta < settings.cooldown_seconds:
                logger.info(f"Factual duplicate scan identified for {identity.id} (delta={delta:.1f}s)")
                return None

        # 3. Resolve student presence events
        if identity.role == Role.STUDENT:
            state = context.student_presence_state or "OUTSIDE"
            
            if state == "OUTSIDE":
                return PresenceEvent(
                    event_type=EventType.STUDENT_ENTER,
                    actor_id=identity.id,
                    actor_role=Role.STUDENT,
                    trigger_source=TriggerSource.SCANNER,
                    metadata={"confidence": context.auth_result.confidence},
                    timestamp=context.current_time
                )
            elif state == "INSIDE":
                return PresenceEvent(
                    event_type=EventType.STUDENT_EXIT,
                    actor_id=identity.id,
                    actor_role=Role.STUDENT,
                    trigger_source=TriggerSource.SCANNER,
                    metadata={"confidence": context.auth_result.confidence},
                    timestamp=context.current_time
                )
            elif state == "STALE":
                return PresenceEvent(
                    event_type=EventType.STUDENT_ENTER,
                    actor_id=identity.id,
                    actor_role=Role.STUDENT,
                    trigger_source=TriggerSource.SCANNER,
                    metadata={"confidence": context.auth_result.confidence, "stale_reconciliation": True},
                    timestamp=context.current_time
                )

        # 4. Resolve faculty presence events
        elif identity.role == Role.FACULTY:
            state = context.faculty_presence_state or "OUTSIDE"
            
            if state == "OUTSIDE":
                return PresenceEvent(
                    event_type=EventType.FACULTY_ENTER,
                    actor_id=identity.id,
                    actor_role=Role.FACULTY,
                    trigger_source=TriggerSource.SCANNER,
                    timestamp=context.current_time
                )
            elif state == "INSIDE":
                return PresenceEvent(
                    event_type=EventType.FACULTY_EXIT,
                    actor_id=identity.id,
                    actor_role=Role.FACULTY,
                    trigger_source=TriggerSource.SCANNER,
                    timestamp=context.current_time
                )

        return None
