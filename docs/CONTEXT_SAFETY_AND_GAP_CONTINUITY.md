# Context Safety and Gap Continuity

**Status:** doctrine / contract (docs-only — no runtime enforcement in this slice)
**Scope:** cross-journey (applies to all non-trivial HLDspec journeys)

---

## Core doctrine

Context safety is a correctness requirement for non-trivial HLDspec journeys.
HLDspec must prevent false completeness caused by context exhaustion, compaction,
unbounded source ingestion, missing decomposition, or lost gaps. Required
evidence, material gaps, assumptions, conflicts, blockers, and
required-but-uninspected areas must be preserved across handoff and session
boundaries. The lead coordinates scope, risk, decisions, and final synthesis; raw
inspection and mechanical execution should be handled by bounded passes or
subagents that return compact receipts.

---

## Context failure modes

Context safety addresses three distinct failure modes:

1. **Hard context limits.** Required information falls out of the active context
   window, retrieval quality degrades, or earlier requirements stop being
   available to the model.

2. **Context dilution.** Required information may still be present, but it is
   buried among code, logs, plans, reviews, discussions, and tool output.
   Signal-to-noise becomes poor, so critical requirements are under-weighted.

3. **Reasoning scope explosion.** A single reasoning process is asked to
   simultaneously hold source understanding, architecture, implementation,
   validation, migration, operations, and approval criteria. Even with enough
   context, local optimizations can break global goals.

Context safety mitigates all three failure modes. Larger context windows reduce
hard limits but do not by themselves solve context dilution or reasoning scope
explosion.

---

## Lead / worker model

The lead owns:

- Scope definition and scope-change decisions.
- Risk assessment and escalation.
- Final synthesis from worker receipts.
- Conflict resolution when receipts disagree.

Workers (bounded passes or subagents) own:

- Inspecting a bounded evidence slice.
- Returning a compact receipt (command, pass/fail, count, and at most 20
  failure lines for test/check passes).
- Not ingesting or summarizing evidence beyond their assigned slice.

Use subagents when available. If subagents are unavailable, use isolated passes
with the same receipt discipline and record the fallback. The requirement does
not depend on a specific tool's subagent implementation.

The lead must not ingest broad raw repo context. The lead may inspect narrow
cited excerpts only when needed for final decision or conflict resolution.

---

## Context isolation

Workers, bounded passes, and subagents are primarily a context-isolation
mechanism, not a parallelism requirement. Their purpose is to give each task a
smaller evidence set, a clearer objective, and fewer competing instructions.

Where feasible, planner, implementer, and validator should be separate roles or
passes. The validator should not rely only on the same reasoning path that
produced the implementation.

---

## Bounded decomposition

For non-trivial repo work: one bounded pass answers one question; one
implementation slice introduces one primary invariant; one test/check pass runs
one command; broad raw logs and source dumps must not enter the lead context. If
subagents are unavailable, use isolated passes with the same receipt discipline
and record the fallback.

Sizing rules:

- A slice is too large if it introduces multiple readiness invariants.
- A worker task is too large if it must answer multiple independent questions.
- A lead context is too large if it contains broad raw evidence that could have
  been summarized by a bounded pass.

---

## Validation-first decomposition

The preferred decomposition flow is:

```
HLD → capabilities → deliverables → atomic tasks
  → independent validation → integration validation
```

This explicitly replaces the unsafe shortcut of jumping directly from HLD to
implementation. Every atomic task should define its proof of correctness before
implementation begins.

Acceptable validation evidence includes:

- Build passes.
- Unit tests pass.
- Contract tests pass.
- Static checks pass.
- Required files exist.
- Required symbols exist.
- Expected behavior is observed.
- Required artifact hashes or manifests are updated.

---

## Atomic-task criteria

An atomic task should be:

- **Independently verifiable** — its proof of correctness does not require
  running unrelated tasks.
- **Independently reviewable** — a reviewer can assess it without understanding
  the full task graph.
- **Independently revertible** — reverting the task does not break unrelated
  completed work.

Agent-facing deliverables are usually smaller than human-facing feature or
component units. Prefer tasks such as adding an interface, implementing an
adapter, adding validation, adding tests, updating a manifest, or updating
documentation over broad tasks such as implementing an entire infrastructure
layer.

---

## Gap continuity

Material gaps must be persisted. Track required-but-uninspected evidence, not
every uninspected file. Gaps may not disappear due to compaction, handoff, or
session reset.

### Gap continuity statuses

These statuses extend the in-process gap statuses defined in
[HLDSPEC_BROWNFIELD_CONTEXT_SAFETY_AND_GAP_LEDGER.md](HLDSPEC_BROWNFIELD_CONTEXT_SAFETY_AND_GAP_LEDGER.md).
The existing contract defines in-process statuses (`RESOLVED_BY_EVIDENCE`,
`NEEDS_OWNER`, `SAFE_TO_DEFER`, `ASSUMED_FOR_NOW`, `BLOCKING`, `CONFLICT`).
This doctrine adds persisted-artifact statuses for cross-session continuity:

| Status | Meaning | Constraint |
|---|---|---|
| `OPEN` | Identified, not yet classified or resolved | Must be resolved before completion |
| `BLOCKING` | Cannot proceed until resolved | (Same semantics as in-process contract) |
| `CONFLICT` | Unresolved disagreement between sources | (Same semantics as in-process contract) |
| `NEEDS_OWNER` | Requires human or role-owner decision | (Same semantics as in-process contract) |
| `ASSUMED_FOR_NOW` | Treated as resolved without full evidence | Requires explicit assumption text |
| `SAFE_TO_DEFER` | Acknowledged, not blocking | Requires reason and scope/owner; must not become a loophole |
| `RESOLVED_BY_EVIDENCE` | Answered by inspected evidence | (Same semantics as in-process contract) |
| `RESOLVED_BY_DECISION` | Answered by explicit human or role-owner decision | Decision reference required |

**Vocabulary note:** the existing in-process contract uses `UNKNOWN` as a gap
*type* (unclassified gap category). This doctrine does not reuse `UNKNOWN` as a
status to avoid collision. Unclassified gaps use status `OPEN` until classified.

### Continuity rules

- A gap present in any worker receipt, session, or handoff artifact must appear
  in the persisted gap ledger.
- `SAFE_TO_DEFER` must record a reason and an owning scope. It must not
  silently absorb gaps that should be `BLOCKING`.
- `ASSUMED_FOR_NOW` must record explicit assumption text so future sessions can
  re-evaluate.
- `RESOLVED_BY_DECISION` must reference the decision (commit, PR, owner
  statement) that resolved it.

---

## Relationship to existing contracts

The in-process context safety contract
([HLDSPEC_BROWNFIELD_CONTEXT_SAFETY_AND_GAP_LEDGER.md](HLDSPEC_BROWNFIELD_CONTEXT_SAFETY_AND_GAP_LEDGER.md))
defines runtime validation computed in-memory during a run, backed by
`hldspec/context_safety_gap_contracts.py` and tested in
`tests_v2/test_context_safety_gap_contracts.py`.

This document defines:

- **Doctrine:** context safety as a named correctness requirement, not just a
  validation rule.
- **Persisted artifacts:** durable JSON files that survive session boundaries,
  compaction, and handoff — which the in-process contract does not cover.
- **Bounded decomposition rules:** sizing discipline for slices, workers, and
  lead context.
- **Gap continuity:** the requirement that material gaps must never disappear
  across boundaries.

The two contracts are complementary. The in-process contract validates a single
run; this doctrine ensures correctness is preserved across runs.

---

## Future implementation roadmap

Enforcement is explicitly staged. This slice is docs-only.

| Phase | What | Depends on |
|---|---|---|
| 1. Doctrine (this PR) | Document the requirement | — |
| 2. Pure validators | Validate persisted artifact structure | Doctrine |
| 3. Producers | Generate artifacts during source-package build | Validators |
| 4. Advisory reports | Surface gap and decomposition state to operators | Producers |
| 5. Gate wiring | Wire artifacts into existing gates | Reports + artifacts exist |

Future persisted artifacts (all under `.hldspec/source_package/`):

- `decomposition_plan.json` — bounded-pass plan for a given task.
- `worker_receipts.json` — compact receipts from workers/bounded passes.
- `gap_ledger.json` — persisted gap state across sessions.
- `evidence_not_inspected.json` — required-but-uninspected evidence.
- `test_runner_receipts.json` — test/check pass results.

---

## Non-goals for this slice

This PR introduces doctrine only. Explicitly out of scope:

- No runtime enforcement or new validators.
- No gate changes or gate wiring.
- No Journey 3 / helper expansion.
- No SpecKit execution changes.
- No Baton edits.
- No parser grammar changes.
- No worker-receipt enforcement.
- No ledger producer.
- No code changes of any kind.
