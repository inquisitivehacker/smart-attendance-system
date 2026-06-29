from enum import Enum


class EventType(str, Enum):
    STUDENT_ENTER = "STUDENT_ENTER"
    STUDENT_EXIT = "STUDENT_EXIT"
    FACULTY_ENTER = "FACULTY_ENTER"
    FACULTY_EXIT = "FACULTY_EXIT"


class TriggerSource(str, Enum):
    SCANNER = "SCANNER"
    MANUAL = "MANUAL"
