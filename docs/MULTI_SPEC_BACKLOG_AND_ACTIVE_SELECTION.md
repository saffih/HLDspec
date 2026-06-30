# Multi-Spec Backlog and Active-Spec Selection Contract

**Status:** Docs-only contract. No runtime enforcement.

**Scope:** Future optional control-plane artifact:
`.hldspec/source_package/spec_backlog.json`

**Non-goals:**

- No validator.
- No producer.
- No selector implementation.
- No source-package manifest changes.
- No target writes.
- No SpecKit execution changes.
- No gate wiring.
- No driver/readiness changes.

---

## Problem

A single HLD can be too large for one implementation spec. HLDspec needs a way
to decompose one HLD into several bounded candidate specs without dumping all of
them into the target repository or overwhelming the implementing agent.

**Unsafe:**
HLD --> one huge spec --> overwhelmed agent / broad target mutation.

**Also unsafe:**
HLD --> many generated target specs at once --> dirty target / unclear active
work.

**Preferred:**
HLD --> control-plane spec backlog --> one selected active spec --> existing
single SpecKit input path (`speckit_single_spec_input.md`).

---

## Minimal-change principle

This contract does not replace the current single-spec flow. It adds an optional
planning layer beside it.

The existing target-facing path remains the single selected spec rendered into
`speckit_single_spec_input.md`. Nothing in this contract changes that path.

---

## Core invariant

Many candidate specs may exist in the HLDspec control plane. At most one spec
may be active. Only the active spec may be rendered into the existing SpecKit
single-spec input path.

No candidate spec may be materialized into the target merely because it exists
in the backlog.

---

## Artifact path

One future artifact:

```
.hldspec/source_package/spec_backlog.json
```

Possible future expansions (not part of this minimal contract):

- `capability_map.json`
- `active_spec.json`
- `spec_packages/`

---

## Top-level JSON shape

```json
{
  "schema_version": 1,
  "created_at": "2026-06-30T12:00:00Z",
  "updated_at": "2026-06-30T12:00:00Z",
  "source_refs": [],
  "active_spec_id": null,
  "specs": []
}
```

Rules:

- `schema_version` is a stable integer.
- `created_at` / `updated_at` are UTC ISO-8601 strings.
- `source_refs` records HLD/source artifacts used to derive the backlog.
- `active_spec_id` is either `null` or exactly one existing `spec_id`.
- `specs` is a list of candidate spec entries.
- `spec_id` values must be unique within `specs`.

---

## Candidate spec fields

**Required fields:**

| Field | Type | Semantics |
|---|---|---|
| `spec_id` | string | Stable ID, e.g. `"SPEC-001"`. |
| `title` | string | Human-readable bounded deliverable title. |
| `hld_anchor_ids` | list of strings | HLD anchors covered by this candidate spec. |
| `capability` | string | One capability or bounded deliverable represented by this spec. |
| `status` | string | Lifecycle state (see allowed statuses below). |
| `size_class` | string | Boundedness indicator (see allowed size classes below). |
| `dependencies` | list of strings | Other `spec_id` values this spec depends on. |
| `validation_strategy` | list of strings | Non-empty list of validation evidence expected before done. |
| `target_materialization` | string | Whether this spec has been rendered into target-facing SpecKit input. |

**Optional fields:**

| Field | Type | Semantics |
|---|---|---|
| `owner_or_scope` | string | Owning journey, role, or scope. |
| `reason` | string | Why this candidate exists. |
| `notes` | string | Free-form notes. |
| `source_refs` | list of strings | Source artifacts specific to this candidate. |

---

## Allowed statuses

| Status | Meaning |
|---|---|
| `PLANNED` | Candidate exists but is not ready for selection. |
| `READY_FOR_SELECTION` | Candidate is bounded and has a validation strategy. |
| `SELECTED` | Active candidate chosen for next work. |
| `MATERIALIZED_TO_TARGET` | Rendered into target-facing single-spec input. |
| `IN_IMPLEMENTATION` | Implementation work started. |
| `VALIDATED` | Validation strategy satisfied. |
| `DONE` | Completed and accepted. |
| `BLOCKED` | Cannot proceed until blocker resolved. |
| `SUPERSEDED` | Replaced by another candidate or decomposition. |

---

## Allowed size classes

| Size class | Meaning |
|---|---|
| `ATOMIC_TASK` | Single independently verifiable task. |
| `BOUNDED_DELIVERABLE` | One capability, one owner, one validation strategy. |
| `SPRINT_SIZED` | Fits within one sprint-sized implementation cycle. |
| `TOO_LARGE` | Requires decomposition before selection. |

Rules:

- `ATOMIC_TASK`, `BOUNDED_DELIVERABLE`, and `SPRINT_SIZED` may become
  `READY_FOR_SELECTION`.
- `TOO_LARGE` must not become `READY_FOR_SELECTION` or `SELECTED`.
- If a candidate needs multiple components, owners, or validation strategies, it
  should be decomposed before selection.

---

## Allowed target materialization states

| State | Meaning |
|---|---|
| `NOT_MATERIALIZED` | Default. Not yet rendered into target. |
| `MATERIALIZED_TO_SINGLE_SPEC_INPUT` | Rendered into the existing `speckit_single_spec_input.md` path. |
| `SUPERSEDED_IN_TARGET` | Previously materialized, now replaced. |

Rules:

- Default is `NOT_MATERIALIZED`.
- Only the active selected spec may become
  `MATERIALIZED_TO_SINGLE_SPEC_INPUT`.
- This contract does not implement materialization.
- Future materialization must record a receipt before or when target-facing files
  are written.

---

## Selection rules

Future validator/selector expectations (contract only, not implemented):

- `active_spec_id` must be `null` or match exactly one `spec_id`.
- If `active_spec_id` is non-null, exactly one spec has status `SELECTED` or
  `MATERIALIZED_TO_TARGET`.
- A selected spec must not have `size_class` `TOO_LARGE`.
- A selected spec must have a non-empty `validation_strategy`.
- A selected spec's dependencies must be `DONE`, `VALIDATED`, or explicitly safe
  to defer.
- Only one selected active spec may be target-facing at a time.

---

## Control-plane / target boundary

The spec backlog is a control-plane artifact. The target repository remains an
evidence and delivery surface. The target must not receive all candidate specs
just because they were derived.

Future implementation should keep the authoritative backlog in the HLDspec
control plane and render only the active selected spec into the existing
single-spec input path (`speckit_single_spec_input.md`).

---

## Example

```json
{
  "schema_version": 1,
  "created_at": "2026-06-30T12:00:00Z",
  "updated_at": "2026-06-30T12:00:00Z",
  "source_refs": [
    "docs/example-hld.md",
    ".hldspec/source_package/hld_reference_map.json"
  ],
  "active_spec_id": "SPEC-001",
  "specs": [
    {
      "spec_id": "SPEC-001",
      "title": "Persisted gap ledger validator",
      "hld_anchor_ids": ["HLD-010", "HLD-011"],
      "capability": "Validate persisted gap ledger shape and state rules",
      "status": "SELECTED",
      "size_class": "BOUNDED_DELIVERABLE",
      "dependencies": [],
      "validation_strategy": ["unit_tests", "contract_tests"],
      "target_materialization": "NOT_MATERIALIZED",
      "owner_or_scope": "Journey 2 validation"
    },
    {
      "spec_id": "SPEC-002",
      "title": "Persisted gap ledger producer",
      "hld_anchor_ids": ["HLD-012"],
      "capability": "Produce gap ledger from known advisory inventory",
      "status": "PLANNED",
      "size_class": "SPRINT_SIZED",
      "dependencies": ["SPEC-001"],
      "validation_strategy": ["unit_tests", "source_package_artifact_check"],
      "target_materialization": "NOT_MATERIALIZED",
      "owner_or_scope": "Future source-package producer"
    }
  ]
}
```

This example has two candidate specs, one selected (`SPEC-001`) and one planned
(`SPEC-002`). `active_spec_id` points to the selected spec. Neither has been
materialized to target yet.

---

## Relationship to existing docs

| Doc | Relationship |
|---|---|
| [`CONTEXT_SAFETY_AND_GAP_CONTINUITY.md`](CONTEXT_SAFETY_AND_GAP_CONTINUITY.md) | Doctrine establishing validation-first decomposition (`HLD --> capabilities --> deliverables --> atomic tasks`). The spec backlog is the future artifact for tracking that decomposition at the spec/deliverable level. |
| [`HLDSPEC_GAP_AND_OPEN_ISSUES_INVENTORY.md`](HLDSPEC_GAP_AND_OPEN_ISSUES_INVENTORY.md) | Gaps SD-1 through SD-4 identify missing spec-size rules, capability sizing, and decomposition artifacts. This contract addresses those gaps at the contract level. |
| [`PERSISTED_GAP_LEDGER_SCHEMA.md`](PERSISTED_GAP_LEDGER_SCHEMA.md) | Recent example of the same sequencing pattern: schema-first contract, then pure validator, then producer, then gate wiring. |

This document follows the same pattern:

1. Contract first (this PR).
2. Pure validator later.
3. Producer later.
4. Gate/materialization later.

---

## Future implementation sequence

1. Define multi-spec backlog contract (this PR).
2. Add pure `spec_backlog.json` validator.
3. Add advisory backlog producer.
4. Add active-spec selector.
5. Render active spec into existing single SpecKit input path.
6. Add materialization receipt.
7. Wire readiness/gate checks.

---

## Non-goals

Explicitly out of scope for this contract:

- No code changes.
- No validator.
- No producer.
- No active selector.
- No artifact generation.
- No source-package manifest changes.
- No gate changes.
- No driver/readiness changes.
- No target writes.
- No multiple target specs.
- No SpecKit execution changes.
- No Baton changes.
- No parser grammar changes.
