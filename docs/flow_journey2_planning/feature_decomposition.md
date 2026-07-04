# Flow Journey 2 — Feature Decomposition

**Date:** 2026-07-04
**Target:** `/Users/saffi/code/flow`
**HLD SHA-256:** `3c376ae9917b05d09d71fd73037b41a800eecbe51eaa5167481f1db11cf7e5d0`
**Output path:** `docs/flow_journey2_planning/` (HLDspec-side; no mutation of target)

---

## Decomposition Constraint

Only the 11 constitution-backed sections are decomposed:
HLD-003, HLD-004, HLD-005, HLD-007, HLD-008, HLD-009, HLD-010, HLD-013,
HLD-014, HLD-015, HLD-016.

The 6 provisional sections (HLD-001, HLD-002, HLD-006, HLD-011, HLD-012,
HLD-017) are deferred. Dependencies on them are flagged with their revisit
triggers in the provisional-dependency register.

---

## Feature Boundaries

### FLOW-F01: Store & Transaction Foundation

| Field | Value |
|---|---|
| `feature_id` | `FLOW-F01` |
| `name` | Store & Transaction Foundation |
| `source_hld_sections` | HLD-003, HLD-013 |
| `dependencies` | (none — root) |
| `purpose` | Define the single-source-of-truth durable store contract, atomic transaction guarantees, and the store→projection derivation boundary. |
| `stop_condition` | The store contract (one durable store, projections derived after commit, WAL+busy_timeout+synchronous=NORMAL) is specified with crash-safety invariants proven. |
| `verification_path` | Concurrent-write tests, crash-recovery tests, projection-after-commit ordering. |

**What it specs:**
- One durable state store is the single source of truth (HLD-003).
- Markdown projections are derived, re-derivable, never part of a transaction (HLD-003).
- Every CLI operation is one all-or-nothing transaction (HLD-013).
- WAL + busy_timeout + synchronous=NORMAL (HLD-013).
- Projection written after commit, not during (HLD-013).

**What it does NOT spec:**
- What the store contains (that's features 02–08).
- CLI verb semantics (features 03–08).
- Which runners use the CLI (provisional — HLD-012).

---

### FLOW-F02: Task Lifecycle & Invariant Discipline

| Field | Value |
|---|---|
| `feature_id` | `FLOW-F02` |
| `name` | Task Lifecycle & Invariant Discipline |
| `source_hld_sections` | HLD-004, HLD-015 |
| `dependencies` | FLOW-F01 |
| `purpose` | Define the four-state task lifecycle, its legal transitions, the dependency guard, and the closed invariant set that constrains the engine. |
| `stop_condition` | State machine fully specified; every guard traces to one of the five invariants (dependency, identity, ownership, lifecycle, existence); the overreach-detection audit is defined. |
| `verification_path` | State-transition coverage, dependency-guard tests, `raise FlowError` tagging audit. |

**What it specs:**
- Four states: pending, in_progress, blocked, done (HLD-004).
- Transition rules: pending→in_progress→done, in_progress→blocked, blocked→pending (wake), done→pending (reopen, rare) (HLD-004).
- The one rule: a task is runnable only with no unmet dependencies (HLD-004).
- done/escalate/split from any non-blocked state — the guard is dependency, not prior state (HLD-004, HLD-015).
- Closed invariant set: dependency, identity, ownership, lifecycle, existence (HLD-015).
- Every `raise FlowError` tagged with the invariant it protects (HLD-015).
- Overreach detection: a guard that can't be tagged is flagged (HLD-015).
- Agent-discretion behaviors are intentional, not defects (HLD-015).

---

### FLOW-F03: Named Sessions, CLI Entry & Work Routing

| Field | Value |
|---|---|
| `feature_id` | `FLOW-F03` |
| `name` | Named Sessions, CLI Entry & Work Routing |
| `source_hld_sections` | HLD-009, HLD-010, HLD-015 |
| `dependencies` | FLOW-F02 |
| `purpose` | Define mandatory named-session enforcement at CLI entry, the verb contract surface, label-based soft affinity, and durable session identity. |
| `stop_condition` | Session enforcement, verb surface, and routing logic fully specified; no anonymous path; identity invariant proven. |
| `verification_path` | Missing-session rejection, affinity-binding tests, fallback-to-any tests, "none" only when no runnable work. |

**What it specs:**
- Every CLI call carries a recognized session, enforced at CLI entry — missing session is an error, reads included (HLD-009).
- Runner-facing verbs: add, next, context, note, decide, done, escalate, split, feedback (HLD-009).
- Human/ops verbs: answer, reopen, reclaim, list — not loop members but callable (HLD-009).
- Permission vs loop membership distinction (HLD-009).
- Runners use only CLI verbs, no direct DB access (HLD-009).
- Session mandatory, first-contact creates row, name is the bracelet (HLD-010).
- Label = task's optional subject; soft affinity: bind on first labeled claim, prefer label, fallback rather than idle (HLD-010).
- "none" only when no runnable work exists (HLD-010).
- Durable identity: reclaim takes the task not the session row (HLD-010).
- Identity invariant: every action by a named session (HLD-015).

---

### FLOW-F04: Fork-Join & Concurrent Escalations

| Field | Value |
|---|---|
| `feature_id` | `FLOW-F04` |
| `name` | Fork-Join & Concurrent Escalations |
| `source_hld_sections` | HLD-005, HLD-004, HLD-015 |
| `dependencies` | FLOW-F02, FLOW-F03 |
| `purpose` | Define the unified fork-join primitive (escalate=split), concurrent-escalation semantics, and wake-on-all-resolved behavior. |
| `stop_condition` | Concurrent escalations, per-escalation stable IDs, partial-answer semantics, and all-resolved wake are specified and testable. |
| `verification_path` | Multi-escalation tests, per-escalation resolution, wake-only-when-all-clear, split→children tests. |

**What it specs:**
- escalate → waits on a human answer; split → waits on child tasks finishing (HLD-005).
- Both park the task as blocked, clear its assignee (label kept), free the runner (HLD-005).
- A task may have multiple escalations open concurrently (HLD-005).
- Each escalation is a distinct dependency with own stable ID/reference, owner/reply routing, status (HLD-005).
- Task wakes to pending only when ALL dependencies resolve (HLD-005).
- Partial answers: an answer resolves exactly the escalation it references; others keep the task parked (HLD-005).
- A task cannot be done with unfinished children or open escalations (HLD-004 via HLD-015 dependency invariant).
- Parking clears assignee; waking re-enters claim flow (HLD-004).

---

### FLOW-F05: Human-in-the-Loop — Answer & Feedback

| Field | Value |
|---|---|
| `feature_id` | `FLOW-F05` |
| `name` | Human-in-the-Loop — Answer & Feedback |
| `source_hld_sections` | HLD-007, HLD-005 |
| `dependencies` | FLOW-F04 |
| `purpose` | Define the answer/feedback discrimination: answer resolves a specific open escalation; feedback steers output or injects scope. |
| `stop_condition` | The two channels fully specified: answer routing to escalation-by-ID, rejection when no match, feedback as report-update or new-task-creation. |
| `verification_path` | Answer-resolves-specific tests, rejected-when-no-open-escalation, feedback-on-report, feedback-as-new-scope. |

**What it specs:**
- The discriminator: "was the task waiting for this?" — yes=answer, no=feedback (HLD-007).
- `answer <id> <text>` — valid only when matching open escalation exists (HLD-007).
- Answer addresses specific escalation by stable ID/reference (implicit when exactly one open) (HLD-007).
- Answer appends to baton, resolves that escalation, wakes task when no deps remain (HLD-007, HLD-005).
- Answer with no matching escalation → rejected (HLD-007).
- `feedback <id> <text>` — steers (HLD-007).
- Feedback on a report → agent-judged update: in-place/section/supersede/sweep (HLD-007).
- Feedback as new scope → creates referenced task (sugar over add + reference) (HLD-007).
- Feedback never forces a state change a guard would forbid (HLD-007).

---

### FLOW-F06: Baton — Context Substrate

| Field | Value |
|---|---|
| `feature_id` | `FLOW-F06` |
| `name` | Baton — Context Substrate |
| `source_hld_sections` | HLD-008, HLD-003, HLD-013 |
| `dependencies` | FLOW-F02, FLOW-F03 |
| `purpose` | Define the per-task blackboard (baton) — its ownership, read/write contract, append-log semantics, and distinction from outcome/report. |
| `stop_condition` | Baton DB-ownership, CLI read path, projection-as-surface, multi-writer note/decide, and within-transaction claim-writes are specified. |
| `verification_path` | Baton read/write tests, claimed-by-on-baton within claim transaction, multi-writer concurrency, projection derivation. |

**What it specs:**
- Baton is DB-owned per-task context substrate — a blackboard (HLD-008).
- Declared context: durable, inspectable, shared, append-log (HLD-008).
- Runner MUST read baton before working (`flow context <id>`) and append progress (`flow note`) (HLD-008).
- Canonical read path is CLI against database; markdown projection is derived surface (HLD-008, HLD-003).
- Projection is product surface with three roles: agent integration/handoff, WIP context state, user-facing reporting (HLD-003).
- Agent may read projection directly when it preserves stable IDs, references, context state, reply context, and report/log links (HLD-003).
- Projections are never a write path (HLD-003).
- `claimed by <session>` recorded on baton within the claim transaction (HLD-013).
- note/decide are blackboard multi-writer — never fenced (HLD-008 via HLD-014).

---

### FLOW-F07: Recovery — Lease, Reclaim, Fence, Flaky-mark

| Field | Value |
|---|---|
| `feature_id` | `FLOW-F07` |
| `name` | Recovery — Lease, Reclaim, Fence, Flaky-mark |
| `source_hld_sections` | HLD-014, HLD-015 |
| `dependencies` | FLOW-F03, FLOW-F04 |
| `purpose` | Define liveness recovery: lease TTL, see-and-act reclaim, ownership fence, permanent flaky-mark with auto-escalation at ceiling. |
| `stop_condition` | All four recovery mechanisms specified; fence rejection proven; flaky-mark ceiling and scoped-escalation behavior defined. |
| `verification_path` | Lease-expiry reclaim, explicit reclaim, fence rejection when held by another, flaky-ceiling escalation, reclaim under BEGIN IMMEDIATE. |

**What it specs:**
- `flow list` surfaces session staleness (HLD-014).
- `flow reclaim <id>` immediately returns observed-non-responsive task (HLD-014).
- Lease TTL (default 1h): task in_progress past TTL reclaimed lazily in `flow next` (HLD-014).
- note/decide refresh lease stamp; silence defines silent task (HLD-014).
- Reclaim returns task to pending, clears assignee, records reason, bumps reclaim_count (HLD-014).
- Only in_progress is reclaimed; blocked is parked by design (HLD-014).
- Reclaim runs under BEGIN IMMEDIATE (HLD-014).
- Permanent flaky-mark: reclaim_count saturates at RECLAIM_MAX (default 3) (HLD-014).
- At/past ceiling: further orphaning escalates immediately with scoped escalation (own ID/reference, reason, routing, coexists with other escalations) (HLD-014, HLD-005).
- Ownership fence: done/escalate/split rejected when task held by different named session (HLD-014, HLD-015:ownership).
- Unowned task stays operable by any named session (HLD-014).
- feedback is unfenced (creation/steering verb, like add) (HLD-014).

---

### FLOW-F08: Output Layer — Outcome & Report

| Field | Value |
|---|---|
| `feature_id` | `FLOW-F08` |
| `name` | Output Layer — Outcome & Report |
| `source_hld_sections` | HLD-016, HLD-003, HLD-015 |
| `dependencies` | FLOW-F02, FLOW-F05, FLOW-F06 |
| `purpose` | Define the three-level output stack (baton/outcome/report), mandatory outcome at done, reports as transcendent subject-scoped deliverables with independent lifecycle. |
| `stop_condition` | Outcome/report distinction specified; report lifecycle (active→deprecated), supersession, immutability of deprecated, feedback-magnitude spectrum, many-to-many, and attributed updates defined. |
| `verification_path` | Mandatory-outcome tests, report lifecycle tests, deprecated-immutable, supersession-aware references, feedback-magnitude dispatch. |

**What it specs:**
- Three levels: baton (context, per-task), outcome (result, per-task, bound), report (deliverable, per-subject, transcendent) (HLD-016).
- Every task has a mandatory outcome at done — its account of what/how/why (HLD-016).
- Outcome size is UX detail: short→inline, long→separate markdown (still an outcome, not a report) (HLD-016).
- A report is a distinct kind: transcendent, subject-scoped, produced deliberately by a report-purposed task (HLD-016).
- Tasks ↔ reports are many-to-many (HLD-016).
- Feedback on report → agent-judged magnitude: tiny=in-place, medium=section, large=supersede, broad=sweep (HLD-016).
- Reports are not ownership-fenced — collaborative deliverables (HLD-016).
- Report lifecycle: active → deprecated (fate: superseded or obsolete) (HLD-016).
- deprecated/obsolete report is immutable (HLD-015:lifecycle invariant) (HLD-016).
- References are deprecation-aware: resolve to live successor (HLD-016).
- Every update is attributed (HLD-016).
- Reports are DB-owned, markdown-projected (HLD-003).

---

## Ordered Features List

This is the single `ordered_features` list from which both the dependency graph
and invocation queue are derived (parity invariant):

```
1. FLOW-F01  Store & Transaction Foundation
2. FLOW-F02  Task Lifecycle & Invariant Discipline
3. FLOW-F03  Named Sessions, CLI Entry & Work Routing
4. FLOW-F04  Fork-Join & Concurrent Escalations
5. FLOW-F05  Human-in-the-Loop — Answer & Feedback
6. FLOW-F06  Baton — Context Substrate
7. FLOW-F07  Recovery — Lease, Reclaim, Fence, Flaky-mark
8. FLOW-F08  Output Layer — Outcome & Report
```

---

## Section Coverage

Every decomposable section appears in at least one feature:

| HLD Section | Covered by features |
|---|---|
| HLD-003 | FLOW-F01, FLOW-F06, FLOW-F08 |
| HLD-004 | FLOW-F02, FLOW-F04 |
| HLD-005 | FLOW-F04, FLOW-F05 |
| HLD-007 | FLOW-F05 |
| HLD-008 | FLOW-F06 |
| HLD-009 | FLOW-F03 |
| HLD-010 | FLOW-F03 |
| HLD-013 | FLOW-F01, FLOW-F06 |
| HLD-014 | FLOW-F07 |
| HLD-015 | FLOW-F02, FLOW-F03, FLOW-F04, FLOW-F07, FLOW-F08 |
| HLD-016 | FLOW-F08 |

All 11 sections covered. No section left unaddressed.
