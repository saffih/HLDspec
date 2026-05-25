# HLDspec Refactor Program (`refactor` branch)

## Objective

Reduce project clutter and improve maintainability by top-down refactoring:

- clearer role boundaries
- stable interfaces and contracts
- smaller modules with single responsibility
- testable seams for behavior changes
- explicit promotion and review gates

No feature expansion is included in this program.

## Operating principles

- Uncle Bob / SOLID: strict boundary ownership and dependency direction.
- Martin Fowler: small, reversible, behavior-preserving refactor slices.
- Kent Beck: tests first for touched behavior, fast feedback each slice.
- RunSkeptic: each critical slice must pass detect/stabilize/evidence before promotion.

## Model routing for this program

Use model tiers by task criticality. Concrete model mapping can be tuned at runtime.

```text
MODEL_ROUTINE  -> deterministic extraction, inventories, code movement prep, scripted cleanup
MODEL_STRONG   -> bounded module refactors, adapter extraction, tests for a single slice
MODEL_CRITICAL -> architecture map, contract changes, role boundaries, promotion decisions, RunSkeptic verdicts
```

Recommended concrete mapping for this branch:

```text
MODEL_ROUTINE:  gpt-5.5 (standard)
MODEL_STRONG:   gpt-5.5 high
MODEL_CRITICAL: gpt-5.5 xhigh
```

Rule: weakest sufficient model creates; strongest necessary model promotes.

## Target architecture groups

Group code and scripts by responsibilities, not by script age or naming style.

1. `core-state`
`hldspec/state_machine.py`, machine contracts, checkpoints, shared state semantics.

2. `machine-orchestration`
`hldspec/machines/*` and orchestration state builders.

3. `hld-parsing-and-classification`
HLD parsing, section classification, conversion plans, marking plans.

4. `speckit-prework-and-quality`
prework plan/package/review/dossier/answer packs and readiness gates.

5. `skeptic-and-review`
RunSkeptic cache/meta review/evidence quality and architecture review tools.

6. `interface-contract-artifacts`
JSON/MD artifact schemas and renderers; file-level contracts and lifecycle.

## Refactor slices (pure refactor order)

Each slice is one commit unless risk requires two commits (prep + move).

### Slice 0: Baseline contracts and guard tests

- Add/align tests that lock current behavior for:
  - state transitions
  - readiness gate semantics
  - artifact promotion statuses
  - spec-list numbering and history classification
- Freeze interfaces used across groups.
- Run RunSkeptic read-only review and record baseline.

Model tier: `MODEL_CRITICAL`.

### Slice 1: Extract shared IO/helpers

- Introduce shared helpers for `load_json`, `write_json`, `sync_dir` selection.
- Replace duplicated helper implementations across scripts.
- Keep outputs byte-compatible where possible.

Model tier: implement with `MODEL_STRONG`, promote with `MODEL_CRITICAL`.

### Slice 2: Separate analyzer vs renderer responsibilities

- In each major script, separate:
  - data build functions
  - decision logic
  - markdown/json rendering
  - CLI I/O
- Ensure build functions are testable without filesystem side effects.

Model tier: `MODEL_STRONG`.

### Slice 3: Enforce role boundaries in orchestration

- Make producer role, assigned agent, model tier, and promotion status explicit where missing.
- Remove ambiguous ownership paths where junior artifacts can be interpreted as approved.
- Keep judge-only promotion invariant central.

Model tier: `MODEL_CRITICAL`.

### Slice 4: Normalize interface/contract artifacts

- Define consistent schema version and required fields for controlling artifacts.
- Add strict validation hooks for critical artifacts before consumption.
- Fail early when artifacts are stale, partially rebuilt, or missing required provenance.

Model tier: `MODEL_CRITICAL`.

### Slice 5: Consolidate SpecKit prework pipeline seams

- Keep current behavior, but reduce coupling between:
  - spec list generation
  - architecture disposition
  - readiness review
- Preserve explicit human approval requirement for disposition promotion.

Model tier: `MODEL_CRITICAL`.

### Slice 6: Cleanup and naming normalization

- Remove dead/legacy naming where not controlling canonical flow.
- Keep compatibility shims only when required by active callers/tests.

Model tier: `MODEL_STRONG`.

## RunSkeptic gate per slice

Before commit:

1. `GATE`: assert scope, done condition, blast radius.
2. `FUNDAMENTAL SCAN`: verify ownership/SoT/interfaces for touched modules.
3. `MAP`: list findings and unknowns (no fixes yet).
4. `STABILIZE + EVIDENCE`: collapse to root causes and evidence level.
5. `DECIDE`: FIX/DECOMPOSE/CONFLICT.
6. `ACT + VERIFY`: smallest reversible change, tests, and regression checks.

Promotion rule: do not mark slice done while ACTION/CONFLICT/blocking unknown remains.

## Verification matrix

Run for every slice:

```text
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s tests_v2 -v
python3 scripts/run_skeptic_meta_review.py --repo /Users/saffi/code/HLDspec --output-dir /private/tmp/hldspec-refactor-runskeptic --fail-on-blocker
git diff --check
```

## Commit format

Use narrow, reviewable commits:

```text
refactor(core-state): extract shared state helpers
refactor(orchestration): enforce judge-only promotion boundaries
refactor(contracts): normalize artifact schema guards
refactor(prework): decouple list/disposition/readiness pipeline
```

## Stop conditions

Stop and escalate to CONFLICT when:

- ownership boundary is unclear
- source of truth is ambiguous
- a change cannot be made reversible
- tests cannot prove behavior preservation
- refactor pressure implies feature redesign

## Branch workflow

Branch: `refactor`

Loop:

```text
pick one slice
run RunSkeptic cycle
apply smallest reversible refactor
run full tests + meta review
commit
repeat
```
