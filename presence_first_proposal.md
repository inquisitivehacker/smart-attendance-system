# Smart Classroom Presence System: Presence-First Architecture Proposal (Revised)

This proposal details the implementation strategy for transitioning the Smart Attendance System into an event-driven **Presence-First Architecture**. In this architecture, physical presence (classroom occupancy) is the primary source of truth, while sessions, academic policies, and attendance are decoupled downstream.

---

## 1. Executive Summary

During prototype verification, we identified that coupling scan validation to session status introduces structural rigidity. In a real-world classroom, students arrive before lecturers, enter during breaks, and exit temporarily. 

The **Presence-First Architecture** models these events as they occur in reality. Physical scanner inputs are resolved into occupancy updates regardless of whether a teaching session is active. Attendance is then calculated as a derived metric by intersecting physical occupancy intervals with academic session windows, governed by institutional rules evaluated in a dedicated policy layer.

---

## 2. Updated Architectural Philosophy

The architecture enforces a strict separation of concerns between physical room tracking and academic policies:

```
┌──────────────────────────────────────────────────────────────────┐
│                      Authentication Layer                        │  ◄── Verifies credentials & biometrics (IdentityService)
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼ [AuthenticationResult]
┌──────────────────────────────────────────────────────────────────┐
│                         Presence Layer                           │
│                                                                  │
│  PresenceEngine                                                  │  ◄── Orchestrates transitions & tracks physical durations
│     └── PresenceStateMachine                                     │  ◄── Enforces transition logic rules (Internal)
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼ [PresenceEvent]
┌──────────────────────────────────────────────────────────────────┐
│                         Session Layer                            │  ◄── Manages session start/end boundaries (SessionManager)
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼ [Session intervals & Presence intervals]
┌──────────────────────────────────────────────────────────────────┐
│                         Policy Layer                             │  ◄── Evaluates institutional policies (PolicyEngine)
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                        Attendance Layer                          │  ◄── Persists derived student attendance records
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Layer-by-Layer Responsibilities

### 3.1 Authentication Layer (`IdentityService`)
* **Role:** Security gatekeeper.
* **Responsibilities:** Barcode validation, registry lookups (via student/faculty repositories), face verification checks, and logging attempts to `authentication_logs`.
* **Constraint:** It has no awareness of classroom occupancy, class session status, or attendance rules.

### 3.2 Presence Layer (`PresenceEngine` & `PresenceStateMachine`)
* **Role:** Custodian of physical classroom occupancy.
* **Responsibilities:** 
  * The `PresenceEngine` acts as the public orchestration layer, receiving resolved events, updating runtime states, and publishing presence events.
  * The `PresenceStateMachine` acts as an **internal component** of the `PresenceEngine`. It is responsible for checking transition logic and updating student/faculty database states (`student_presence_states`).
* **Factual Occupancy Rule:** Faculty is treated exactly like students from the perspective of the Presence layer. The PresenceEngine tracks whether a faculty member is physically `"INSIDE"` or `"OUTSIDE"` the room, without attaching any academic session meaning to that presence.

### 3.3 Session Layer (`SessionManager`)
* **Role:** Tracks temporal teaching windows.
* **Responsibilities:** Listens to presence events. When a `FACULTY_ENTER` event is published, `SessionManager` starts the teaching session; when `FACULTY_EXIT` is published, it ends the session.
* **Constraint:** It does not control scanner validation or presence state mutations.

### 3.4 Policy Layer (`PolicyEngine`)
* **Role:** Governs business rules.
* **Responsibilities:** Evaluates academic rules (cooldowns, attendance duration thresholds, late arrival constraints, regularization categories) by intersecting presence intervals and session windows.
* **Constraint:** Neither the PresenceEngine nor the SessionManager holds any knowledge of these policies.

---

## 4. Revised Execution Flow

```
Scanner Input
     │
     ▼
IdentityService ──► [Write: authentication_logs]
     │
     ▼ [AuthenticationResult]
RuntimeContextBuilder (Future)
     │
     ▼ [EventContext]
EventResolver
     │
     ▼ [PresenceEvent | None]
PresenceEngine (Public orchestration)
     │
     ├── Injects context into: PresenceStateMachine (Internal rules logic)
     ├── Updates DB table: student_presence_states
     └── Publishes resolved PresenceEvent
             │
             ├──► SessionManager (Consumes FACULTY_ENTER/EXIT to start/end sessions)
             │
             └──► PolicyEngine (Combines Presence ∩ Session intervals to write Attendance)
```

---

## 5. Attendance Derivation Model

Attendance is computed by the `PolicyEngine` at session completion or on-demand using interval intersection math:

$$\text{Participation Duration} = \sum \Big( [\text{Presence Enter}_i, \text{Presence Exit}_i] \;\cap\; [\text{Session Start}, \text{Session End}] \Big)$$

This keeps attendance records fully re-calculable and history-independent. If the institutional rule threshold changes (e.g., from 75% to 80% for the `PRESENT` mark), the system re-evaluates the query over the raw database intervals without having to modify historical logs.

---

## 6. Cooldown Behaviour

* **Signals Filter:** Cooldown acts as a physical noise filter. Its purpose is to prevent key bounces or double scans from causing the state machine to toggle states rapidly (e.g. `INSIDE` $\rightarrow$ `OUTSIDE` $\rightarrow$ `INSIDE`).
* **Decoupled from Attendance:** Because cooldown protects the physical presence state rather than grading rules, it belongs to the Presence Layer. Duplicate scans resolve to `None`, meaning no event occurred and the state remains unchanged.

---

## 7. Proposed Milestone 4 Plan: PresenceEngine Implementation

Milestone 4 will focus on implementing the Presence Layer logic:

### 7.1 Key Tasks
1. **Model Updates:** Set up the ORM model mapping to `student_presence_states` (created in Milestone 1).
2. **`PresenceStateMachine` (Internal):** Implement transition checks and state updates (`INSIDE`, `OUTSIDE`, `STALE`), tracking duration values (`inside_since` and `accumulated_seconds`).
3. **`PresenceEngine` (Public):** Implement the orchestrator class that manages state updates and triggers database writes inside transaction boundaries.
4. **AttendanceEngine Integration (Temporary):** Modify `AttendanceEngine` to call `PresenceEngine` to update states, while maintaining legacy session start/end calculations temporarily.

---

## 8. Migration Implications

* **Session Decoupling:** The logic starting sessions on faculty scans will move out of `AttendanceEngine` and into the future `SessionManager` in a later milestone.
* **Unified State Store:** Student state checks (currently mapping to the pilot `student_states` table) will migrate to `student_presence_states` once the state machines are integrated.
