# Brownfield Context Safety and Gap Ledger

**Status:** product contract
**Scope:** cross-journey (applies to all journeys)
**Implementation:** `hldspec/context_safety_gap_contracts.py`
**Tests:** `tests_v2/test_context_safety_gap_contracts.py`

---

## Purpose

For large-evidence, repo-archaeology, HLD/SDD, product-recovery, state-model
recovery, persistence-safety recovery, or implementation-planning workflows,
HLDspec requires structured context safety to prevent lost gaps, hidden
assumptions, context overload, and unsafe build planning.

This contract defines the mandatory Gap Ledger, worker decomposition discipline,
evidence mapping, and RunSkeptic reconciliation rules.

**Core correctness rule:** lost gaps and missing coverage are correctness
failures, not style issues.

---

## When this contract applies

Any workflow where:

- Evidence corpus exceeds what a single model context can safely hold.
- Multiple workers/subagents inspect bounded evidence slices.
- A lead agent synthesizes worker receipts into a plan.
- Gaps must be classified before build planning proceeds.
- Recovery, brownfield discovery, or large-document analysis is involved.

---

## Required concepts

### Gap types

| Type | Meaning |
|---|---|
| `PRODUCT_GAP` | Missing product requirement, user journey, or acceptance criterion |
| `STATE_MODEL_GAP` | State machine invariant violation or missing transition |
| `PERSISTENCE_GAP` | Durability, backup, export, or data-loss risk |
| `MIGRATION_GAP` | Schema migration, version transition, or upgrade path gap |
| `DATA_SAFETY_GAP` | Data corruption, integrity, WAL/SHM, or transaction safety gap |
| `UI_FLOW_GAP` | User interface flow, navigation, or interaction gap |
| `TEST_GAP` | Missing test coverage, test gate, or validation gap |
| `ARCHITECTURE_GAP` | Boundary, coupling, dependency, or interface gap |
| `CONTRADICTION` | Two sources of evidence disagree |
| `ASSUMPTION` | Unverified assumption treated as fact |
| `UNKNOWN` | Unclassified — must be resolved before build planning |

### Gap statuses

| Status | Meaning | Constraint |
|---|---|---|
| `RESOLVED_BY_EVIDENCE` | Gap answered by inspected evidence | — |
| `NEEDS_OWNER` | Requires owner decision | Must be `blocking=True` or have `owner_decision_scope` |
| `SAFE_TO_DEFER` | Acknowledged, not blocking | Evidence must still be recorded |
| `ASSUMED_FOR_NOW` | Treated as resolved without full evidence | Requires explicit `assumption_text` |
| `BLOCKING` | Cannot proceed until resolved | Makes the plan unsafe |
| `CONFLICT` | Unresolved disagreement | Must be surfaced in verdict |

---

## Rules

### No gap may disappear

Every gap identified by any worker must appear in the final Gap Ledger.
The verdict function recomputes worker-gap coverage from receipts and blocks
on any missing gap. Stored reconciliation fields are never trusted.

### Classification before planning

No gap may remain with type `UNKNOWN` in the final ledger. All gaps must be
classified into a specific type before build planning proceeds.

### Worker decomposition

When available, large-evidence tasks require worker/subagent decomposition.
Decomposition means multiple bounded workers (`min_worker_count`, default 2),
not a single worker relabeled. A single receipt is not decomposition.
Workers inspect bounded evidence and return compact receipts. The lead
synthesizes from receipts, not raw full context. Self-served tickets (lead
inspects evidence directly instead of dispatching a worker) are process
coverage gaps, not style issues — they must be recorded.

### Compact receipts

Worker receipts must not exceed the configured byte limit
(`max_worker_receipt_bytes`, default 50,000). Total receipt volume must not
exceed the lead context limit (`max_lead_context_bytes`, default 200,000).

### Evidence tracking

- An evidence map is required.
- Evidence not inspected must be explicitly recorded (not omitted).
- Owner-declared non-required evidence may be `SAFE_TO_DEFER` but must remain
  recorded in `owner_declared_not_required` and traceable — either referenced
  in a gap item description or in RunSkeptic reconciliation notes.

### RunSkeptic reconciliation

RunSkeptic reconciliation of worker gaps to final ledger to plan is required
before the verdict can be safe. The reconciliation object must be present
(not None).

### Authority boundary

This contract grants no:

- Approval authority
- Implementation authority
- Work-order authority
- Speckit execution authority
- Product-decision authority
- Target-repo mutation authority

All authority flags on `ContextSafetyRules` default to `False` and must remain
so. Any `True` grant makes the verdict unsafe.

---

## Baton calibration edge cases

These edge cases from the Baton Flow brownfield recovery calibrate what the
contract must be able to represent:

| Edge case | Representation |
|---|---|
| Large brownfield evidence (313KB doc) | Context limits, mandatory decomposition |
| v1/v2 canonical ambiguity | `NEEDS_OWNER` with `owner_decision_scope` |
| WAL/SHM corruption hypothesis | `DATA_SAFETY_GAP` + `ASSUMED_FOR_NOW` with text |
| Assignee-clearing invariant violation | `STATE_MODEL_GAP` |
| No backup/export | `PERSISTENCE_GAP` |
| Owner-declared non-required evidence | `SAFE_TO_DEFER` + `owner_declared_not_required` |
| Stage 0 test-only constraint | `TEST_GAP` |
| Broad coding before gap classification | Blocked by `UNKNOWN` gap type rule |

Baton is a calibration fixture, not a coding target. This contract does not
implement Baton-specific logic.

---

## Validation contract

A final plan is unsafe if:

1. Any worker gap is missing from the final ledger.
2. Any gap remains unclassified (type `UNKNOWN`).
3. Any `BLOCKING` gap exists.
4. Any `CONFLICT` gap is not surfaced.
5. `ASSUMED_FOR_NOW` lacks explicit `assumption_text`.
6. `NEEDS_OWNER` lacks `blocking=True` or `owner_decision_scope`.
7. Worker receipts exceed compactness limits.
8. Lead ingests too much raw context.
9. Fewer than `min_worker_count` workers when decomposition is required.
10. Gap ledger is empty when required.
11. RunSkeptic reconciliation is missing or failed.
12. Evidence not inspected is not recorded.
13. Owner-declared non-required evidence is not traceable.
14. Any authority grant is `True`.

See `tests_v2/test_context_safety_gap_contracts.py` for the executable version.
