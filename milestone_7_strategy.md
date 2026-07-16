# Smart Classroom Presence System: Milestone 7 — PolicyEngine & Attendance Derivation (Revised Blueprint)

This document contains the final architectural blueprint and implementation design for **Milestone 7: PolicyEngine & Attendance Derivation**. This revision refines domain boundaries, establishes the `AttendanceAssembler` layer, details `AttendanceRecord` mapping schemas, and defines transaction and idempotency scopes.

---

## 1. High-Level Architecture

The target pipeline isolates raw database logs from domain validations and persistence representations:

```mermaid
flowchart TD
    subgraph Facts
        E[PresenceEvents Log]
    end

    subgraph Evaluation Pipeline (Pure Domain)
        IB[IntervalBuilder]
        PE[ParticipationEvaluator]
        ENG[PolicyEngine]
        ASM[AttendanceAssembler]
    end

    subgraph Projections (Mutable)
        REC[AttendanceRecord Schema]
        REP[AttendanceRepository]
        TAB[(attendance Table)]
    end

    E ──► IB
    IB ──► |PresenceIntervals| PE
    PE ──► |ParticipationMetrics| ENG
    ENG ──► |AttendanceDecision| ASM
    ASM ──► |AttendanceRecord| REC
    REC ──► REP
    REP ──► TAB
```

---

## 2. Service Responsibilities

### 2.1 `IntervalBuilder` (Pure Domain Service)
* **Responsibility:** Reconstructs continuous, chronological occupancy intervals ($[t_{\text{enter}}, t_{\text{exit}}]$) from raw `PresenceEvent` logs for a specific student.
* **Dependencies:** None.
* **Boundaries:** Pure domain logic. No ORM access, no queries, and no transaction knowledge.

### 2.2 `ParticipationEvaluator` (Pure Domain Service)
* **Responsibility:** Intersects occupancy intervals with the session lecture window to calculate factual duration metrics.
* **Dependencies:** None.
* **Boundaries:** Pure domain logic. Restricts calculations to time difference mathematics and entry/exit counts.

### 2.3 `PolicyEngine` (Pure Domain Service)
* **Responsibility:** Evaluates objective metrics against the active `InstitutionPolicy` schema to resolve classification outcomes.
* **Dependencies:** `InstitutionPolicy` configuration.
* **Boundaries:** Pure domain logic. Resolves classifications deterministically without query locks.

### 2.4 `AttendanceAssembler` (Pure Domain Service)
* **Responsibility:** Combines domain outputs (`AttendanceDecision` and `ParticipationMetrics`) with relational data (student metadata, session parameters) to compile a persistence-ready `AttendanceRecord`.
* **Dependencies:** None.
* **Boundaries:** Pure mapper logic. No database connections.

### 2.5 `AttendanceDerivationService` (Application Orchestrator)
* **Responsibility:** Coordinates pipeline execution.
  1. Loads events and session details using repositories.
  2. Invokes domain evaluators and mappers.
  3. Manages database transaction commit/rollback boundaries.
* **Dependencies:** `PresenceEventRepository`, `SessionRepository`, `AttendanceRepository`, `IntervalBuilder`, `ParticipationEvaluator`, `PolicyEngine`, `AttendanceAssembler`.
* **Boundaries:** Application layer. Only this orchestrator is allowed to interact with database sessions.

---

## 3. Domain Model Schemas

Domain objects are defined as immutable Pydantic schemas:

### 3.1 `PresenceInterval`
* `enter_time`: `datetime` (UTC entry timestamp)
* `exit_time`: `datetime | None` (UTC exit timestamp, or `None` if currently inside)

### 3.2 `ParticipationMetrics`
* `participation_seconds`: `int` (Total seconds present inside slot)
* `participation_percentage`: `float` (Ratio of presence to session duration)
* `late_minutes`: `int` (Minutes elapsed between session start and first entry)
* `early_departure_minutes`: `int` (Minutes elapsed between last exit and session end)
* `entries`: `int` (Total physical entries recorded during class)
* `exits`: `int` (Total physical exits recorded during class)
* `entered_before_session`: `bool` (True if entered before class started)
* `inside_at_session_end`: `bool` (True if inside when class ended)

### 3.3 `PolicyContext`
* `session_id`: `int`
* `metrics`: `ParticipationMetrics`
* `policy`: `InstitutionPolicy`

### 3.4 `AttendanceDecision`
* `status`: `str` (`"PRESENT"`, `"ABSENT"`, `"REGULARIZATION"`)
* `present`: `bool` (Binary indicator)
* `regularization_required`: `bool` (True if regularization thresholds are met)
* `reason`: `str` (Classification description, e.g. `"grace_period_exceeded"`)
* `policy_id`: `str` (Reference ID of policy evaluated)
* `policy_version`: `str` (Version string of policy evaluated)
* `computed_at`: `datetime` (UTC evaluation time)

### 3.5 `AttendanceRecord`
* `student_id`: `str`
* `session_id`: `int`
* `participation_seconds`: `int`
* `participation_percentage`: `float`
* `status`: `str`
* `regularization_required`: `bool`
* `late_minutes`: `int`
* `early_departure_minutes`: `int`
* `policy_version`: `str`
* `computed_at`: `datetime`

### 3.6 `InstitutionPolicy`
* `policy_id`: `str` (e.g. `"POL-01"`)
* `version`: `str` (e.g. `"1.2"`)
* `effective_from`: `datetime`
* `effective_to`: `datetime | None`
* `minimum_attendance_percentage`: `float`
* `late_grace_minutes`: `int`
* `early_exit_grace_minutes`: `int`
* `regularization_threshold`: `float`
* `allow_multiple_entries`: `bool`
* `count_breaks`: `bool`
* `maximum_break_minutes`: `int`
* `medical_override_enabled`: `bool`

---

## 4. Transaction Boundaries & Idempotency

### 4.1 Session-Level Transaction Scope
Derivation occurs in a single database transaction:
* **All-or-Nothing:** The `AttendanceDerivationService` opens a transaction, derives attendance records for all active students registered in the slot, and executes a single `db.commit()` at the end.
* **Consistency:** If derivation fails for a single student (e.g., integrity constraints or null errors), the transaction rolls back completely, leaving the database consistent.

### 4.2 Idempotency Guarantees
Derivation calculations must be idempotent:
* **Constraint Implementation:** The `AttendanceRepository` executes updates using an upsert pattern. When writing `AttendanceRecord` models:
  * If a record with `(student_id, session_id)` already exists, the repository overwrites its metrics and status fields.
  * If not, a new row is appended.
* **Execution Safety:** Running the derivation service multiple times over identical inputs will yield exactly the same projection table output, preventing duplicate entries.

---

## 5. Trigger Model

The `AttendanceDerivationService` operates independently of triggers:

```
┌─────────────────────────────────┐
│          Trigger Source         │
└────────────────┬────────────────┘
                 ├─► [Session Closed] ───────► (Faculty exit triggers derivation)
                 ├─► [Manual Recalculation] ─► (Admin overrides trigger calculation)
                 ├─► [Policy Updated] ───────► (Re-running historic session range)
                 └─► [Nightly Verification] ──► (Cron reconciles gaps)
```

---

## 6. Future Compatibility

* **CQRS (Command Query Responsibility Segregation):** The write ledger (`presence_events`) remains clean. Analytical reports fetch data from the read-optimized projection table (`attendance`), preserving fast load speeds.
* **EventDispatcher Integration:** In later milestones, `AttendanceDerivationService` will run inside an event observer callback (e.g. listening for a `SessionClosed` event broadcast) without modifications.

---

## 7. Critical Self-Review

### Potential Bottlenecks
* **Bulk Calculations:** Loading all events for large classes at session closure could introduce latency.
* **Mitigation:** We will introduce query filters to retrieve events within the lecture duration window ($t_{\text{start}}$ to $t_{\text{end}}$), reducing the row search space.

### Remaining Architectural Debt
* **In-memory Faculty Tracking:** Decoupling faculty state mutations from server memory (slated for database migration in Milestone 8).
* **Direct Compatibility Mappings:** Temporarily logging student scans inside `AttendanceEngine.process_scan()`. These writes will be removed once the `PolicyEngine` derivation integration is complete.
