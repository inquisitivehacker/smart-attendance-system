import logging
from datetime import datetime
from src.schemas.attendance_policy import PolicyContext, AttendanceDecision

logger = logging.getLogger(__name__)


class PolicyEngine:
    """
    Pure domain service responsible for determining final attendance classifications.
    Provides deterministic outcomes given a PolicyContext.
    """

    @staticmethod
    def evaluate(context: PolicyContext) -> AttendanceDecision:
        """
        Evaluates ParticipationMetrics against InstitutionPolicy parameters.
        Returns a structured AttendanceDecision.
        """
        metrics = context.metrics
        policy = context.policy

        status = "ABSENT"
        present = False
        reg_required = False
        reason = "unresolved"

        # 1. Check if participation is below the absolute regularization floor
        if metrics.participation_percentage < policy.regularization_threshold:
            status = "ABSENT"
            present = False
            reg_required = False
            reason = "insufficient_participation_below_threshold"

        # 2. Check if participation is above floor but below the minimum required percentage
        elif metrics.participation_percentage < policy.minimum_attendance_percentage:
            status = "REGULARIZATION"
            present = False
            reg_required = True
            reason = "insufficient_participation_above_threshold"

        # 3. Participation meets minimum requirements, check grace periods
        else:
            if metrics.late_minutes > policy.late_grace_minutes:
                status = "REGULARIZATION"
                present = False
                reg_required = True
                reason = "exceeded_late_grace_period"
            elif metrics.early_departure_minutes > policy.early_exit_grace_minutes:
                status = "REGULARIZATION"
                present = False
                reg_required = True
                reason = "exceeded_early_exit_grace_period"
            else:
                status = "PRESENT"
                present = True
                reg_required = False
                reason = "met_all_requirements"

        return AttendanceDecision(
            status=status,
            present=present,
            regularization_required=reg_required,
            reason=reason,
            policy_id=policy.policy_id,
            policy_version=policy.version,
            computed_at=datetime.utcnow()
        )
