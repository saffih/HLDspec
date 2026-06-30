# Persisted Gap Ledger Schema

**Status:** Docs-only schema contract.

**Scope:** Future `.hldspec/source_package/gap_ledger.json`.

**Non-goal:** No validator, no producer, no advisory report, no gate wiring, no runtime enforcement, no code.

---

## Purpose

`gap_ledger.json` is intended to preserve material gaps across context compaction, handoff, and session boundaries.

> The gap ledger prevents false completeness by making unresolved gaps explicit, stateful, reviewable, and carryable across runs.

Without a persisted ledger, gaps discovered in one session may be silently dropped during compaction or lost during handoff, producing a false sense of completeness in later sessions.

---

## Relationship to existing docs

| Doc | Relationship |
|---|---|
| [`HLDSPEC_GAP_AND_OPEN_ISSUES_INVENTORY.md`](HLDSPEC_GAP_AND_OPEN_ISSUES_INVENTORY.md) | Current human-readable inventory of known gaps and open issues. The ledger schema defined here is the future machine-readable counterpart. |
| [`CONTEXT_SAFETY_AND_GAP_CONTINUITY.md`](CONTEXT_SAFETY_AND_GAP_CONTINUITY.md) | Doctrine establishing gap continuity as a correctness requirement. The ledger is the intended persisted artifact for that doctrine. |
| [`HLDSPEC_BROWNFIELD_CONTEXT_SAFETY_AND_GAP_LEDGER.md`](HLDSPEC_BROWNFIELD_CONTEXT_SAFETY_AND_GAP_LEDGER.md) | In-process context-safety validation contract with its own gap ledger concept. The persisted artifact defined here complements (does not replace) the in-process contract. |

This PR defines the future persisted artifact shape. It does not implement the artifact.

---

## Artifact path

```
.hldspec/source_package/gap_ledger.json
```

---

## Top-level JSON shape

The artifact is a JSON **object**, not a bare list.

```json
{
  "schema_version": 1,
  "created_at": "2026-06-30T12:00:00Z",
  "updated_at": "2026-06-30T12:00:00Z",
  "source_refs": [],
  "gaps": []
}
```

### Top-level fields

| Field | Type | Required | Description |
|---|---|---|---|
| `schema_version` | integer | yes | Stable schema version. Starts at `1`. Bumped only on breaking changes. |
| `created_at` | string | yes | UTC ISO-8601 timestamp of initial creation. |
| `updated_at` | string | yes | UTC ISO-8601 timestamp of last modification. |
| `source_refs` | list of strings | yes | Docs/source artifacts used to create or update the ledger (e.g., `"docs/HLDSPEC_GAP_AND_OPEN_ISSUES_INVENTORY.md"`). |
| `gaps` | list of gap entries | yes | Gap entries. `gap_id` values must be unique across all entries. |

---

## Gap entry fields

### Required fields

| Field | Type | Description |
|---|---|---|
| `gap_id` | string | Unique identifier for this gap. Must be unique across all entries in `gaps`. |
| `category` | string | Gap category. Must be one of the allowed values below. |
| `state` | string | Current gap state. Must be one of the allowed values below. |
| `summary` | string | Human-readable summary of the gap. |
| `why_it_matters` | string | Why this gap is material — what breaks, degrades, or becomes unreliable if unaddressed. |
| `source_refs` | list of strings | Where this gap was identified (doc paths, section references, evidence). |
| `created_at` | string | UTC ISO-8601 timestamp of when this gap entry was created. |
| `updated_at` | string | UTC ISO-8601 timestamp of last modification to this entry. |

### Optional / conditionally required fields

| Field | Type | Condition | Description |
|---|---|---|---|
| `owner_or_scope` | string | Required for `SAFE_TO_DEFER`; recommended for `NEEDS_OWNER` | Who owns resolution, or what scope bounds the gap. |
| `reason` | string | Required for `SAFE_TO_DEFER` | Why deferral is safe. |
| `assumption_text` | string | Required for `ASSUMED_FOR_NOW` | The assumption being made and its boundary conditions. |
| `evidence_ref` | string | Required for `RESOLVED_BY_EVIDENCE` | Pointer to the evidence that resolves the gap (file path, commit, PR, section). |
| `decision_ref` | string | Required for `RESOLVED_BY_DECISION` | Pointer to the decision that resolves the gap (file path, commit, PR, section). |
| `related_gap_ids` | list of strings | Recommended for `CONFLICT` | Other gap IDs involved in the conflict. |
| `notes` | string | optional | Free-text notes. For `CONFLICT` entries, should explain the conflicting sources if `related_gap_ids` is absent. |

---

## Allowed `category` values

Drawn from the gap inventory:

| Category | Scope |
|---|---|
| `context_safety_and_gap_continuity` | Gap continuity, context compaction survival, persisted artifacts |
| `spec_capability_decomposition` | Spec splitting, dependency tracking, capability decomposition |
| `control_plane_isolation` | Control state vs target state separation |
| `journey2_sdd_completeness` | SDD coverage ledger, HLD-to-SDD traceability |
| `validation_architecture` | Schema validation, contract enforcement, validator coverage |
| `testing_discipline` | Test coverage, test strategy, characterization tests |
| `driver_readiness` | Driver capabilities, readiness reporting, operator state |
| `journey3_helper_execution` | Helper contract execution, helper bootstrap, completion tracking |
| `speckit_helper_scope` | SpecKit-specific helper behavior, run card, slice control |
| `baton_external_workflow` | External workflow handoff, cross-repo coordination |
| `docs_governance` | Documentation accuracy, staleness, cross-reference integrity |

---

## Allowed `state` values

| State | Meaning |
|---|---|
| `OPEN` | Identified, not yet addressed. |
| `BLOCKING` | Actively blocks downstream work. |
| `CONFLICT` | Contradictory information from multiple sources. |
| `NEEDS_OWNER` | No clear owner or scope assigned. |
| `ASSUMED_FOR_NOW` | Proceeding under an explicit assumption that may not hold. |
| `SAFE_TO_DEFER` | Acknowledged, safe to defer with documented reason and owner. |
| `RESOLVED_BY_EVIDENCE` | Resolved by observable evidence (code, test, artifact). |
| `RESOLVED_BY_DECISION` | Resolved by an explicit decision (PR, design doc, review). |
| `PARTIAL` | Something exists but does not fully satisfy the requirement. |
| `KNOWN_LIMITATION` | Accepted limitation — not a hidden blocker. |

### `UNKNOWN` is not a valid persisted state

`UNKNOWN` is deliberately excluded from the persisted gap state vocabulary. Existing in-process contracts (e.g., Journey 0 evidence labels, brownfield gap types) use `UNKNOWN` as a gap type or evidence label. Reusing it as a persisted status would create ambiguity between "we haven't classified this gap yet" and "we observed an unknown condition." Persisted gaps must have an explicit state from the vocabulary above.

---

## State transition and conditional field rules

| State | Required fields | Notes |
|---|---|---|
| `SAFE_TO_DEFER` | `reason`, `owner_or_scope` | Must document why deferral is safe and who owns eventual resolution. |
| `ASSUMED_FOR_NOW` | `assumption_text` | Must state the assumption and its boundary conditions. |
| `RESOLVED_BY_EVIDENCE` | `evidence_ref` | Must point to the evidence. |
| `RESOLVED_BY_DECISION` | `decision_ref` | Must point to the decision. |
| `CONFLICT` | `related_gap_ids` or `notes` | Must explain the conflicting sources. |
| `NEEDS_OWNER` | `owner_or_scope` (when known) | Should include scope even if owner is unassigned. |

### Compaction and handoff survival rules

`OPEN`, `BLOCKING`, `CONFLICT`, and `NEEDS_OWNER` entries must not be silently dropped during handoff or context compaction. A producer or compaction process that encounters these states must preserve them in the output ledger.

### Semantic constraints

- `PARTIAL` means something exists but does not fully satisfy the requirement. It is not a synonym for `OPEN`.
- `KNOWN_LIMITATION` means an accepted limitation with conscious acknowledgment. It is not a synonym for `SAFE_TO_DEFER` — a known limitation has no expectation of future resolution.

---

## Minimal example

```json
{
  "schema_version": 1,
  "created_at": "2026-06-30T12:00:00Z",
  "updated_at": "2026-06-30T14:30:00Z",
  "source_refs": [
    "docs/HLDSPEC_GAP_AND_OPEN_ISSUES_INVENTORY.md",
    "docs/CONTEXT_SAFETY_AND_GAP_CONTINUITY.md"
  ],
  "gaps": [
    {
      "gap_id": "CTX-001",
      "category": "context_safety_and_gap_continuity",
      "state": "OPEN",
      "summary": "Worker receipts are not persisted to a machine-readable artifact",
      "why_it_matters": "Without persisted receipts, context compaction may discard evidence of what workers actually checked, producing gaps in traceability.",
      "source_refs": ["docs/HLDSPEC_GAP_AND_OPEN_ISSUES_INVENTORY.md#context-safety"],
      "created_at": "2026-06-30T12:00:00Z",
      "updated_at": "2026-06-30T12:00:00Z"
    },
    {
      "gap_id": "CPI-002",
      "category": "control_plane_isolation",
      "state": "PARTIAL",
      "summary": "Control-plane isolation boundary is documented but not enforced by validators",
      "why_it_matters": "Without enforcement, control state may leak into target artifacts or vice versa, violating ownership boundaries.",
      "source_refs": ["docs/HLDSPEC_GAP_AND_OPEN_ISSUES_INVENTORY.md#control-plane"],
      "created_at": "2026-06-30T12:00:00Z",
      "updated_at": "2026-06-30T14:30:00Z",
      "notes": "Boundary documented in TOOLCHAIN_DRIVER_BOUNDARY.md; no runtime validator exists yet."
    },
    {
      "gap_id": "SKH-003",
      "category": "speckit_helper_scope",
      "state": "SAFE_TO_DEFER",
      "summary": "SpecKit helper scope boundaries not yet codified as testable contract",
      "why_it_matters": "Without a testable contract, helper scope may expand beyond intended authority during Journey 3 execution.",
      "source_refs": ["docs/HLDSPEC_GAP_AND_OPEN_ISSUES_INVENTORY.md#speckit-helper"],
      "owner_or_scope": "Journey 3 helper execution track",
      "reason": "Journey 3 helper execution is not yet active; scope contract can be defined when helper bootstrap is implemented.",
      "created_at": "2026-06-30T12:00:00Z",
      "updated_at": "2026-06-30T12:00:00Z"
    }
  ]
}
```

---

## Validation expectations (future PRs)

A future pure validator should check:

- Top-level object shape (not a bare list, all required fields present).
- Required fields present on every gap entry.
- `state` values are from the allowed set.
- `category` values are from the allowed set.
- `gap_id` values are unique across all entries.
- Conditional required fields are present when their state demands them.
- Timestamp fields are valid UTC ISO-8601 if a shared timestamp format is standardized elsewhere.
- No `UNKNOWN` state value.
- Unresolved gaps (`OPEN`, `BLOCKING`, `CONFLICT`, `NEEDS_OWNER`) are preserved — a validator run after compaction should not find fewer unresolved gaps than the input unless an explicit state transition was recorded.

This validator is not implemented by this PR.

---

## Non-goals

This document explicitly does not:

- Change any code.
- Add any new Python module.
- Implement schema validation.
- Implement a source-package producer for `gap_ledger.json`.
- Change the source-package manifest.
- Change any gate behavior.
- Change driver or readiness reporting.
- Change Journey 3 or helper behavior.
- Change SpecKit execution behavior.
- Change Baton or external workflow behavior.
- Change any parser grammar.
- Claim that `gap_ledger.json` exists today.
