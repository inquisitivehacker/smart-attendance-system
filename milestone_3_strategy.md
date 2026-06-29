# Smart Attendance System: Milestone 3 — EventResolver & Event Model Strategy (Revised)

This document outlines the revised implementation strategy for **Milestone 3: EventResolver & Event Model**. In this revision, we align the architecture with a strict separation between physical classroom facts and business policies.

---

## 1. Design Philosophy Refinements

The role of the `EventResolver` is to answer exactly one question:
> **"What physical fact just occurred in the classroom?"**

It does **not** evaluate whether a scan is valid for attendance, whether a session should start or end, or whether a scan is a duplicate. Policies are decoupled from the event-resolution layer, allowing future rules to change without modifying the underlying event definition.

### Summary of Key Architectural Refinements:
* **Factual Events Only:** Removed policy-derived events like `NO_ACTIVE_SESSION` and `DUPLICATE_SCAN`. If a student scans, they entered or exited. If a scan occurred within the cooldown window, it did not alter classroom state, so the resolver resolves it as `None` (no event).
* **Faculty Occupancy vs. Session Controls:** Replaced `SESSION_START` and `SESSION_END` with `FACULTY_ENTER` and `FACULTY_EXIT`. The arrival of a teacher is a physical fact; whether that arrival starts a class is a session policy.
* **Factual Context Only:** Removed the derived `is_duplicate` flag from the `EventContext`. It now contains raw variables like `last_scan_timestamp`, leaving the evaluation of cooldown limits to the resolver.
* **Separation of Context Construction:** Added design details for a future `RuntimeContextBuilder` component to extract context compilation logic out of `AttendanceEngine` in later milestones.

---

## 2. Updated Execution Flow

The decoupled validation and decision pipeline operates as follows:

```
[Scan Input (Barcode, Frame)]
             │
             ▼
┌──────────────────────────┐
│      IdentityService     │ ──► Audits credentials in authentication_logs
└────────────┬─────────────┘
             │
             ▼ [AuthenticationResult]
┌──────────────────────────┐
│     AttendanceEngine     │ ──► Queries raw database context
└────────────┬─────────────┘
             │
             ▼ [EventContext (Factual)]
┌──────────────────────────┐
│       EventResolver      │ ──► Resolves event type (pure function, no DB writes)
└────────────┬─────────────┘
             │
             ▼ [PresenceEvent | None]
┌──────────────────────────┐
│ AttendanceEngine (temp)  │ ──► Maps resolved events to legacy database writes
└──────────────────────────┘
```

---

## 3. Revised EventType Enum Design

The `EventType` is restricted strictly to physical events that occurred in the room:

```python
from enum import Enum

class EventType(str, Enum):
    STUDENT_ENTER = "STUDENT_ENTER"
    STUDENT_EXIT = "STUDENT_EXIT"
    FACULTY_ENTER = "FACULTY_ENTER"
    FACULTY_EXIT = "FACULTY_EXIT"
    AUTH_FAILED = "AUTH_FAILED"
```

* **Why `AUTH_FAILED` is retained:** An authentication failure (e.g. invalid format or biometric reject) is a physical, auditable event at the classroom door.
* **Handling Duplicates:** A scan that triggers the cooldown check does not change the occupant's state. The resolver resolves this as `None` instead of generating an event.

---

## 4. Revised PresenceEvent Model Design

The resolved `PresenceEvent` is an immutable schema representing a point-in-time fact:

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from src.schemas.event_types import EventType
from src.schemas.identity import Role

class PresenceEvent(BaseModel):
    model_config = ConfigDict(frozen=True)  # Guarantees immutability

    event_id: int | None = None
    event_version: str = "1.0"
    event_type: EventType
    actor_id: str
    actor_role: Role
    classroom_id: str = "Room-1"
    timestamp: datetime
    metadata: dict | None = None  # Diagnostic metadata (e.g., face confidence, camera ID)
```

---

## 5. Revised EventContext Design

`EventContext` contains only factual, raw parameters rather than processed business outcomes:

```python
from datetime import datetime
from pydantic import BaseModel
from src.schemas.identity import AuthenticationResult

class EventContext(BaseModel):
    auth_result: AuthenticationResult
    student_presence_state: str | None = None  # 'INSIDE' | 'OUTSIDE' | 'STALE'
    faculty_presence_state: str | None = None  # 'INSIDE' | 'OUTSIDE'
    last_scan_timestamp: datetime | None = None # Timestamp of last recorded scan (for cooldown checks)
    current_time: datetime
```

### Purpose of Fields:
* `student_presence_state` / `faculty_presence_state`: Tracks the current state of the actor inside the classroom.
* `last_scan_timestamp`: The raw timestamp of the actor's last recorded successful scan, allowing the resolver to run cooldown evaluations without hardcoding flags.
* `current_time`: The timezone-aware timestamp of the current attempt.

---

## 6. Event Resolution Rules Matrix

The `EventResolver` resolves incoming context objects using the following rules:

### 6.1 Decision Rules Matrix
* **Rule 1: Authentication Failed**
  * *Condition:* `auth_result.authenticated == False`
  * *Result:* `PresenceEvent(event_type=EventType.AUTH_FAILED)`
* **Rule 2: Duplicate Scan (Cooldown Trigger)**
  * *Condition:* `last_scan_timestamp` is not None AND (`current_time` - `last_scan_timestamp` < `cooldown_seconds`)
  * *Result:* `None` (no event is triggered; state does not change)
* **Rule 3: Student Entry (New Scan)**
  * *Condition:* Actor is `STUDENT` AND `student_presence_state` is `OUTSIDE` (or `None`)
  * *Result:* `PresenceEvent(event_type=EventType.STUDENT_ENTER)`
* **Rule 4: Student Exit**
  * *Condition:* Actor is `STUDENT` AND `student_presence_state` is `INSIDE` (health: `NORMAL`)
  * *Result:* `PresenceEvent(event_type=EventType.STUDENT_EXIT)`
* **Rule 5: Student Re-entry (Stale Reconciliation)**
  * *Condition:* Actor is `STUDENT` AND `student_presence_state` is `INSIDE` (health: `STALE`)
  * *Result:* `PresenceEvent(event_type=EventType.STUDENT_ENTER)` *(Implicit reconciliation of stale status)*
* **Rule 6: Faculty Entry**
  * *Condition:* Actor is `FACULTY` AND `faculty_presence_state` is `OUTSIDE` (or `None`)
  * *Result:* `PresenceEvent(event_type=EventType.FACULTY_ENTER)`
* **Rule 7: Faculty Exit**
  * *Condition:* Actor is `FACULTY` AND `faculty_presence_state` is `INSIDE`
  * *Result:* `PresenceEvent(event_type=EventType.FACULTY_EXIT)`

---

## 7. Integration & Compatibility Plan

### 7.1 Files to Create
* **`src/schemas/event_types.py`:** Contains the `EventType` enum.
* **`src/schemas/event_context.py`:** Contains the `EventContext` schema.
* **`src/schemas/presence_event.py`:** Contains the `PresenceEvent` model definition.
* **`src/services/event_resolver.py`:** Contains the pure `EventResolver` logic.
* **`tests/test_event_resolver.py`:** Unit tests verifying the decision resolver.

### 7.2 Files to Modify
* **`src/services/attendance_engine.py`:**
  * Instantiates `EventResolver` on startup.
  * In `process_scan()`, queries the database parameters, constructs `EventContext`, calls `self.event_resolver.resolve_event(context)`, and maps the returned event back to existing derived updates.
  * *Cleanup:* Removes the unused `StudentRepository` import as deferred in Milestone 2.

### 7.3 Future Context Builder Migration Path
For Milestone 3, `AttendanceEngine` compiles the `EventContext` manually inside `process_scan`. In later milestones, this logic will be extracted into a dedicated `RuntimeContextBuilder` service:
```python
# Future implementation detail (Milestone 4+):
context = self.context_builder.build_context(scanned_id, auth_result, db)
event = self.event_resolver.resolve_event(context)
```

---

## 8. Milestone Boundaries

The following operations are outside the scope of Milestone 3:
* **Derived Attendance Calculations:** Marking session percentages and total seconds remains under legacy engine logic.
* **Session Lifecycles:** Starting and ending classes continues to write directly to the `sessions` table.
* **Event Persistence:** Saving events to the database will be handled by the `PresenceEngine` in Milestone 5.

---

## 9. Testing Strategy

### 9.1 Decision Rules Unit Tests (`tests/test_event_resolver.py`)
Tests decision resolutions by passing mock context states:
* Injects student context with `student_presence_state='INSIDE'`, asserts result is `EventType.STUDENT_EXIT`.
* Injects student context with `student_presence_state='INSIDE'` and `last_scan_timestamp` within cooldown limit, asserts result is `None`.
* Injects student context with `student_presence_state='STALE'`, asserts result is `EventType.STUDENT_ENTER`.
* Injects faculty context with `faculty_presence_state='OUTSIDE'`, asserts result is `EventType.FACULTY_ENTER`.

### 9.2 API Regression Testing
Runs curl calls to confirm endpoint backward compatibility:
```bash
curl -X POST http://localhost:8000/api/attendance/test-scan \
  -H "Content-Type: application/json" \
  -d '{"student_id": "SET-12584"}'
```
*Expected: `{"success":false,"error":"No active session"}`.*
