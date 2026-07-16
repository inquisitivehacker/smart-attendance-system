import logging
from src.schemas.attendance_policy import AttendanceRecord, ParticipationMetrics, AttendanceDecision

logger = logging.getLogger(__name__)


class AttendanceAssembler:
    """
    Pure domain service mapping metrics and policy decisions into a persistence-ready AttendanceRecord.
    Has zero side effects or database access dependencies.
    """

    @staticmethod
    def assemble(
        student_id: str,
        session_id: int,
        metrics: ParticipationMetrics,
        decision: AttendanceDecision
    ) -> AttendanceRecord:
        """
        Combines metrics, decision status, and references into a structured AttendanceRecord.
        """
        return AttendanceRecord(
            student_id=student_id,
            session_id=session_id,
            participation_seconds=metrics.participation_seconds,
            participation_percentage=metrics.participation_percentage,
            status=decision.status,
            regularization_required=decision.regularization_required,
            late_minutes=metrics.late_minutes,
            early_departure_minutes=metrics.early_departure_minutes,
            policy_version=decision.policy_version,
            computed_at=decision.computed_at
        )
