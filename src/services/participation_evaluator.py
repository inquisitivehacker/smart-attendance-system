import logging
from datetime import datetime
from src.schemas.attendance_policy import PresenceInterval, ParticipationMetrics

logger = logging.getLogger(__name__)


class ParticipationEvaluator:
    """
    Pure domain evaluator to compute objective attendance metrics.
    Operates mathematically on intervals and session windows with zero persistence logic.
    """

    @staticmethod
    def evaluate(
        intervals: list[PresenceInterval],
        session_start: datetime,
        session_end: datetime
    ) -> ParticipationMetrics:
        """
        Intersects occupancy intervals with the session window to calculate factual metrics.
        Implements interval clipping (excluding time outside of class hours).
        """
        session_duration = (session_end - session_start).total_seconds()
        if session_duration <= 0:
            raise ValueError("Session duration must be positive")

        participation_seconds = 0
        entries = len(intervals)
        exits = sum(1 for i in intervals if i.exit_time is not None)

        # 1. Compute clipped participation seconds
        for interval in intervals:
            # Clip interval enter time
            start = max(interval.enter_time, session_start)
            # Clip interval exit time (default to session end if open interval)
            exit_time = interval.exit_time if interval.exit_time is not None else session_end
            end = min(exit_time, session_end)

            if start < end:
                delta = (end - start).total_seconds()
                participation_seconds += int(delta)

        participation_percentage = (participation_seconds / session_duration) * 100.0

        # 2. Compute late arrival minutes
        late_minutes = 0
        entered_before_session = False
        if intervals:
            first_enter = intervals[0].enter_time
            if first_enter < session_start:
                entered_before_session = True
            elif first_enter <= session_end:
                late_minutes = max(0, int((first_enter - session_start).total_seconds() / 60))

        # 3. Compute early departure minutes and whether student was inside at end
        early_departure_minutes = 0
        inside_at_session_end = any(
            i.enter_time <= session_end and (i.exit_time is None or i.exit_time >= session_end)
            for i in intervals
        )

        if intervals:
            last_interval = intervals[-1]
            last_exit = last_interval.exit_time
            if last_exit is not None and last_exit < session_end:
                early_departure_minutes = max(0, int((session_end - last_exit).total_seconds() / 60))


        return ParticipationMetrics(
            participation_seconds=participation_seconds,
            participation_percentage=round(participation_percentage, 2),
            late_minutes=late_minutes,
            early_departure_minutes=early_departure_minutes,
            entries=entries,
            exits=exits,
            entered_before_session=entered_before_session,
            inside_at_session_end=inside_at_session_end
        )
