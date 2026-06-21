"""
Timetable service — preserved from prototype lines 30-49.
Made configurable instead of hardcoded.
"""
from datetime import datetime


DEFAULT_SLOTS = [
    ("Hour 1", 525, 585),   # 08:45 - 09:45
    ("Hour 2", 585, 645),   # 09:45 - 10:45
    ("Break",  645, 660),   # 10:45 - 11:00
    ("Hour 3", 660, 720),   # 11:00 - 12:00
    ("Hour 4", 720, 780),   # 12:00 - 01:00
    ("Lunch",  780, 840),   # 01:00 - 02:00
    ("Hour 5", 840, 890),   # 02:00 - 02:50
    ("Hour 6", 890, 940),   # 02:50 - 03:40
]


class TimetableService:
    def __init__(self, slots: list = None):
        self.slots = slots or DEFAULT_SLOTS

    def get_current_slot(self) -> str:
        """Preserved from prototype get_current_slot()."""
        now = datetime.now()
        minutes = now.hour * 60 + now.minute
        for name, start, end in self.slots:
            if start <= minutes < end:
                return name
        return "After Hours"

    def is_break(self) -> bool:
        """Check if the current slot is a break period."""
        slot = self.get_current_slot()
        return slot in ("Break", "Lunch")

    def get_all_slots(self) -> list[dict]:
        """Return all slots for display/API purposes."""
        result = []
        for name, start, end in self.slots:
            start_h, start_m = divmod(start, 60)
            end_h, end_m = divmod(end, 60)
            result.append({
                "name": name,
                "start": f"{start_h:02d}:{start_m:02d}",
                "end": f"{end_h:02d}:{end_m:02d}",
            })
        return result
