# Smart Attendance System: Milestone 2 — IdentityService Implementation Strategy

This document outlines the engineering strategy for implementing **Milestone 2: IdentityService**. The objective is to extract all authentication logic from the current `AttendanceEngine` into a dedicated `IdentityService` layer while preserving 100% backward compatibility and keeping existing interfaces unchanged.

---

## 1. Current Authentication Flow

In the current implementation, authentication and session/presence calculations are mixed inside `AttendanceEngine`. The pipeline operates as follows:

```
[Physical Scanner Scan]
          │
          ▼
┌────────────────────────┐
│  src/hardware_loop.py  │  • Grabs barcode event via ScannerService.read_barcode()
│      HardwareLoop      │  • Grabs video frame copy via CameraService.get_latest_frame()
│     _scanner_loop()    │  • Enqueues (barcode, frame) into self.scan_queue
└─────────┬──────────────┘
          │ (Queue Dispatch)
          ▼
┌────────────────────────┐
│  src/hardware_loop.py  │  • Dequeues item inside background worker thread
│      HardwareLoop      │  • Opens db session SessionLocal()
│      _worker_loop()    │  • Invokes AttendanceEngine.process_scan()
└─────────┬──────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│             src/services/attendance_engine.py | AttendanceEngine            │
│                              process_scan()                                 │
│                                                                             │
│  0. Active Session Check: Query SessionRepository.get_active()              │
│     Dependencies: SessionRepository, SQLite sessions table                  │
│                                                                             │
│  1. Barcode Format Verification: Local regular expression character filter  │
│                                                                             │
│  2. Student Identity Check: Query StudentRepository.get_by_id()             │
│     Dependencies: StudentRepository, SQLite students table                  │
│                                                                             │
│  3. Cooldown Check: Query AttendanceRepository.get_last_successful_scan()   │
│     Dependencies: AttendanceRepository, SQLite scan_logs table              │
│                                                                             │
│  4. Face Verification: Invokes FaceService.verify(frame, student_id)        │
│     Dependencies: FaceService (OpenCV, face_recognition, dlib libraries)    │
│                                                                             │
│  5. Timetable Slot Mapping: Invokes TimetableService.get_current_slot()     │
│                                                                             │
│  6. Audit Logging: Invokes AttendanceRepository.log_scan()                  │
│     Dependencies: AttendanceRepository, SQLite scan_logs table              │
│                                                                             │
│  7. Presence Commit: Transitions student state and marks present in DB      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Proposed Authentication Flow

After Milestone 2, the pipeline is decoupled. Authentication resolution moves into `IdentityService`, returning an authenticated `Identity` model:

```
[Scan Input (Barcode, Frame)]
             │
             ▼
┌────────────────────────┐
│      HardwareLoop      │  • Intercepts inputs as before, maintaining queue and threads
└─────────┬──────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 src/services/attendance_engine.py | AttendanceEngine            │
│                              process_scan()                                 │
│                                                                             │
│  * Delegates authentication tasks by invoking IdentityService.authenticate() │
└─────────┬───────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                  src/services/identity_service.py | IdentityService         │
│                               authenticate()                                │
│                                                                             │
│  • Runs barcode validation format checks                                    │
│  • Checks if scanned ID exists in students or faculty tables                │
│  • Performs dlib face embedding matches if student matches                  │
│  • Writes detailed attempt metrics to the new authentication_logs database  │
│  • Returns a resolved Identity dataclass object back to caller              │
└─────────┬───────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 src/services/attendance_engine.py | AttendanceEngine            │
│                              process_scan()                                 │
│                                                                             │
│  * Evaluates the returned Identity status                                  │
│  * Proceeds with session validation, cooldown checks, and DB commits        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Step-by-Step Implementation Sequence

To avoid breaking existing interfaces, we will implement Milestone 2 in the following order:

### Step 3.1: Define the `Identity` Dataclass Model
* **Why:** Creates a standard model object representing resolved actor states.
* **Changes:** Create [src/schemas/identity.py](file:///Users/adheem/barcode-face-project/src/schemas/identity.py) containing a Pydantic model or standard dataclass:
  ```python
  from pydantic import BaseModel

  class Identity(BaseModel):
      id: str
      role: str          # "STUDENT" | "FACULTY" | "UNKNOWN"
      name: str
      authenticated: bool
      face_verified: bool
      confidence: float | None = None
      status: str        # "SUCCESS" | "REJECTED_FACE" | "UNKNOWN_BARCODE" | "INVALID_FORMAT"
  ```

### Step 3.2: Create the `IdentityService`
* **Why:** Centralizes format checking, database lookups, biometric verification, and logging attempts.
* **Changes:** Create [src/services/identity_service.py](file:///Users/adheem/barcode-face-project/src/services/identity_service.py).
  * Moves format checks from `AttendanceEngine._validate_barcode`.
  * Instantiates or is injected with `FaceService` to execute biometric verification.
  * Queries `students` and `faculty` tables to resolve actor roles.
  * Logs attempts to `authentication_logs` and the legacy `scan_logs` table (to maintain backward compatibility for this milestone).

### Step 3.3: Refactor the `AttendanceEngine`
* **Why:** Decouples authentication logic, making it responsible only for session and presence business rules.
* **Changes:** Modify [src/services/attendance_engine.py](file:///Users/adheem/barcode-face-project/src/services/attendance_engine.py).
  * Inject `IdentityService` on initialization.
  * In `process_scan()`, replace format validation, database student queries, face matching, and audit logging with a call to:
    ```python
    identity = self.identity_service.authenticate(scanned_id, frame, db, skip_face_verification)
    ```
  * If the returned `identity` status is not `SUCCESS` (or `authenticated` is `False`), reject the scan using the identity's specific rejection reason.
  * If `SUCCESS`, proceed with the cooldown checks, active session checks, state machine transitions, and marking present.
  * **Result:** The function signature of `process_scan` remains unchanged, preserving full compatibility with APIs and the hardware daemon thread.

---

## 4. File-Level Changes

| File | Action | Reason |
| :--- | :--- | :--- |
| **[src/schemas/identity.py](file:///Users/adheem/barcode-face-project/src/schemas/identity.py)** | **CREATE** | New data container representing authenticated identity states. |
| **[src/services/identity_service.py](file:///Users/adheem/barcode-face-project/src/services/identity_service.py)** | **CREATE** | Encapsulates formatting, database lookups, biometric matching, and audit logging. |
| **[src/services/attendance_engine.py](file:///Users/adheem/barcode-face-project/src/services/attendance_engine.py)** | **MODIFY** | Delegates authentication to `IdentityService`, keeping the class focused on session management. |
| **[src/hardware_loop.py](file:///Users/adheem/barcode-face-project/src/hardware_loop.py)** | **NO CHANGE** | Interaction with `AttendanceEngine.process_scan()` remains identical. |
| **[src/api/attendance.py](file:///Users/adheem/barcode-face-project/src/api/attendance.py)** | **NO CHANGE** | Testing route `/api/attendance/test-scan` continues to call `process_scan` unchanged. |
| **[src/main.py](file:///Users/adheem/barcode-face-project/src/main.py)** | **MODIFY** | Instantiates `IdentityService` on startup and injects it into `AttendanceEngine`. |

---

## 5. IdentityService Design

### 5.1 Structure & Code Skeleton
```python
from sqlalchemy.orm import Session as DBSession
from src.services.face_service import FaceService
from src.schemas.identity import Identity
from src.models.student import Student
from src.models.faculty import Faculty
from src.models.authentication_log import AuthenticationLog
from src.models.scan_log import ScanLog
from datetime import datetime

class IdentityService:
    def __init__(self, face_service: FaceService):
        self.face_service = face_service

    def authenticate(
        self, barcode: str, frame, db: DBSession, skip_face: bool = False
    ) -> Identity:
        # 1. Barcode Format Verification
        if not self._validate_barcode(barcode):
            self._log_attempt(db, barcode, None, "UNKNOWN", False, None, "INVALID_FORMAT")
            return Identity(
                id=barcode, role="UNKNOWN", name="Unknown",
                authenticated=False, face_verified=False, status="INVALID_FORMAT"
            )

        # 2. Check Faculty Database Directory
        faculty = db.query(Faculty).filter(Faculty.id == barcode).first()
        if faculty:
            self._log_attempt(db, barcode, faculty.id, "FACULTY", True, 1.0, "SUCCESS")
            return Identity(
                id=faculty.id, role="FACULTY", name=faculty.name,
                authenticated=True, face_verified=True, confidence=1.0, status="SUCCESS"
            )

        # 3. Check Student Database Directory
        student = db.query(Student).filter(Student.id == barcode).first()
        if not student:
            self._log_attempt(db, barcode, None, "UNKNOWN", False, None, "UNKNOWN_BARCODE")
            return Identity(
                id=barcode, role="UNKNOWN", name="Unknown",
                authenticated=False, face_verified=False, status="UNKNOWN_BARCODE"
            )

        # 4. Biometric Face Verification
        verified = False
        confidence = 0.0
        if skip_face:
            verified, confidence = True, 1.0
        else:
            if frame is not None:
                verified, confidence = self.face_service.verify(frame, student.id)

        # 5. Route Result
        if verified:
            status = "SUCCESS"
            self._log_attempt(db, barcode, student.id, "STUDENT", True, confidence, status)
            return Identity(
                id=student.id, role="STUDENT", name=student.name,
                authenticated=True, face_verified=True, confidence=confidence, status=status
            )
        else:
            status = "REJECTED_FACE"
            self._log_attempt(db, barcode, student.id, "STUDENT", False, confidence, status)
            return Identity(
                id=student.id, role="STUDENT", name=student.name,
                authenticated=False, face_verified=False, confidence=confidence, status=status
            )

    def _validate_barcode(self, barcode: str) -> bool:
        if len(barcode) > 12 or len(barcode) < 5:
            return False
        if not barcode.startswith(("21", "22", "23", "SET")):
            return False
        return True

    def _log_attempt(self, db: DBSession, raw_barcode: str, resolved_id: str | None, role: str, verified: bool, confidence: float | None, status: str):
        # A. Write to the new authentication_logs database table
        log = AuthenticationLog(
            barcode_scanned=raw_barcode,
            resolved_id=resolved_id,
            actor_type=role,
            face_verified=1 if verified else 0,
            face_confidence=confidence,
            status=status,
            scanned_at=datetime.utcnow()
        )
        db.add(log)
        
        # B. Write to the legacy scan_logs table to keep existing live-monitor APIs functional
        # Note: ONLY write to scan_logs if student or faculty matches. Invalid formats are discarded as before.
        if status in ("SUCCESS", "REJECTED_FACE"):
            legacy_log = ScanLog(
                student_id=resolved_id or raw_barcode,
                scan_type="entry",
                face_verified=1 if verified else 0,
                face_confidence=confidence,
                slot="Hour 1", # default placeholder, resolved by engine later
                scanned_at=datetime.utcnow()
            )
            db.add(legacy_log)
        db.commit()
```

---

## 6. AttendanceEngine Refactor Plan

### 6.1 Removed Logic
* The validation checks inside `_validate_barcode()`.
* Direct calls to `self.face_service.verify()`.
* Direct database writes to `scan_logs` inside `AttendanceRepository.log_scan()`.

### 6.2 Retained Logic
* Active session validation (`SessionRepository.get_active()`).
* Database-backed cooldown lookup (`AttendanceRepository.get_last_successful_scan()`).
* Student presence state transitions (`StudentStateMachine.transition()`).
* Attendance marking updates (`AttendanceRepository.mark_present()`).

### 6.3 Input Integration Changes
To maintain backward compatibility, the signature of `process_scan` is unchanged:
```python
def process_scan(self, scanned_id: str, frame, db: DBSession, skip_face_verification: bool = False) -> dict:
```
Internally, the refactored method calls `IdentityService` and maps the output back to the existing return schema:
```python
identity = self.identity_service.authenticate(scanned_id, frame, db, skip_face_verification)
if not identity.authenticated:
    if identity.status == "INVALID_FORMAT":
        return {"status": "rejected", "reason": "invalid_format"}
    if identity.status == "UNKNOWN_BARCODE":
        return {"status": "rejected", "reason": "unknown_student", "student_id": scanned_id}
    if identity.status == "REJECTED_FACE":
        return {"status": "denied", "student_id": scanned_id, "student_name": identity.name, "reason": "face_mismatch", "confidence": identity.confidence}

# If verified, proceed with active session, cooldown, state machine, and marking present:
...
```

---

## 7. Hardware Loop Changes

Because the call signature of `AttendanceEngine.process_scan()` remains unchanged, **no modifications are required** in `hardware_loop.py`. The hardware daemon process will query the cameras and read scanner inputs as before.

---

## 8. API Impact Assessment

* **GET `/api/health`:** No impact.
* **POST `/api/attendance/test-scan`:** No impact. Calls `process_scan` with `skip_face_verification=True` and receives the same response payload.
* **GET `/api/attendance/live`:** No impact. Reads scan events from `scan_logs` (which are populated by `IdentityService` for backward compatibility during this milestone).
* **GET `/api/dashboard/summary`:** No impact.

---

## 9. Database Usage

| Table Name | Operations During Milestone 2 |
| :--- | :--- |
| `authentication_logs` | **Write:** Every validation attempt creates an entry here. No updates or deletes. |
| `scan_logs` | **Write:** `IdentityService` writes verified student scan results here to maintain compatibility with existing APIs. |
| `students` | **Read:** `IdentityService` queries this table to verify student IDs. |
| `faculty` | **Read:** `IdentityService` queries this table to verify faculty IDs. |
| `sessions` | **Read:** `AttendanceEngine` checks if an active session is running. |
| `attendance` | **Write:** `AttendanceEngine` inserts records for successful, session-authorized scans. |

---

## 10. Testing Plan

### 10.1 Unit / Integration Tests
* **Test Case 1: Invalid Barcode Format**
  * **Input:** Scan `"ABC"` (invalid characters, length < 5).
  * **Verification:** Verify `IdentityService` returns `status="INVALID_FORMAT"`, `authenticated=False`, and writes a record to `authentication_logs`.
* **Test Case 2: Unknown Barcode ID**
  * **Input:** Scan `"SET-99999"` (correct format, missing from database).
  * **Verification:** Verify `IdentityService` returns `status="UNKNOWN_BARCODE"`, and writes a log to `authentication_logs`.
* **Test Case 3: Faculty Card Scan**
  * **Input:** Scan `"FAC-01"`.
  * **Verification:** Verify `IdentityService` resolves role as `"FACULTY"`, `authenticated=True`, and writes a log to `authentication_logs`.
* **Test Case 4: Face Verification Denied**
  * **Input:** Scan `"SET-12584"` with mismatched camera frame.
  * **Verification:** Verify `IdentityService` returns `status="REJECTED_FACE"`, `authenticated=False`, and creates a log.

### 10.2 REST API Verification
Run curl calls to verify that the existing endpoints continue to function correctly:
```bash
curl -X POST http://localhost:8000/api/attendance/test-scan \
  -H "Content-Type: application/json" \
  -d '{"student_id": "SET-12584"}'
```
*Expected output: `{"success":false,"error":"No active session"}` (identical to legacy server status).*

---

## 11. Risks & Mitigation Plans

* **Circular Dependency Risk:**
  * *Risk:* `AttendanceEngine` imports `IdentityService`, and `IdentityService` needs elements from `AttendanceEngine`.
  * *Mitigation:* Ensure `IdentityService` has no dependency on the engine. It only uses SQLAlchemy models, repositories, and `FaceService`.
* **Database Contention on `authentication_logs`:**
  * *Risk:* Recording every authentication attempt (including failed ones) increases database writes.
  * *Mitigation:* Wrap log writes inside isolated transaction scopes. SQLite WAL mode handles concurrent write queues efficiently.

---

## 12. Success Criteria

1. `AttendanceEngine` delegates formatting, lookups, and face matching to `IdentityService`.
2. `IdentityService` is the single entry point for biometric matching and role resolution.
3. Every scan attempt creates a record in `authentication_logs`.
4. Existing `scan_logs` entries are written to maintain compatibility with live monitors.
5. `/api/attendance/test-scan` returns identical JSON payloads for both valid and invalid scans.
