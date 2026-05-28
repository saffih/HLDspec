# SpecKit Slice Control

## Purpose

HLDspec uses one complete HLD as the product source of truth, then asks SpecKit to create one complete spec, plan, task graph, and analysis pass. Implementation is not executed all at once by default. HLDspec controls implementation through approved slices.

The goal is to avoid losing requirements while still keeping each implementation pass small, testable, and reviewable.

## Core rule

Do not split the HLD to make smaller specs.

Instead:

```text
One full HLD
-> one HLDspec source package
-> one SpecKit specify
-> one SpecKit plan
-> one SpecKit tasks graph
-> one SpecKit analyze pass
-> many approved implementation slices
```

SpecKit plans the whole product once. HLDspec controls implementation slice by slice.

## Ownership

HLDspec owns:

```text
.hldspec/source_package/
```

SpecKit owns:

```text
.specify/
specs/
implementation artifacts
```

HLDspec may mirror source-package files into:

```text
.specify/source/
```

but `.specify/source/` is generated read-only context for SpecKit. It is not the source of truth.

## Why slices exist

SpecKit can create a complete plan and tasks for the full product. But implementation may be too large or risky to run in one pass.

Slice control lets HLDspec say:

```text
The full product is known.
The full task graph is known.
Only this selected part may be implemented now.
```

## What "control" means (HLDspec provides, the user/mediator enforces)

HLDspec **generates** the slice scope (`implementation_slices.json`,
`implementation_slicing_policy.md`) and **bounds** each implementation pass with
allowed task IDs, forbidden files, anchors, tests, and stop conditions. HLDspec does
**not** execute or hard-enforce slices at runtime — the **user or Agent Mediator**
enforces the boundary by deciding when to go, stop, clarify, rerun tests, or reassess.
Slices are guidance/scope handed to the implementer, not phases HLDspec runs itself.

## Generated source-package artifacts

HLDspec writes the slice-control artifacts under `.hldspec/source_package/` and
mirrors them as generated read-only context under `.specify/source/`:

```text
implementation_slicing_policy.md
implementation_slices.json
slice_test_policy.md
speckit_slice_execution_prompt.md
anchor_coverage_schema.json
```

## Canonical slices and tests

### FOUNDATION

Workspace, build/test commands, project scaffold, SpecKit initialization validation.

No product behavior.

Required tests/checks:

```text
build command exists and runs
test command exists and runs
source package mirror exists
workspace layout is valid
```

### WALKING_SKELETON

Minimal runnable system path with placeholders.

Required tests/checks:

```text
app starts
one smoke command, endpoint, or path works
invalid config fails clearly
```

### DOMAIN_MODEL

Entities, value objects, statuses, invariants, domain errors.

Must not depend on database, API, CLI, UI, or network.

Required tests/checks:

```text
entity creation tests
value object validation tests
invalid state rejection tests
status transition tests
```

### CONTRACTS

Ports, interfaces, DTOs, schemas, API/event contracts.

Required tests/checks:

```text
schema validation tests
DTO shape tests
port contract tests
invalid payload tests
```

### BUSINESS_LOGIC

Use cases, workflows, validation rules, state transitions.

Required tests/checks:

```text
use-case tests
workflow tests
business rule tests
error-path tests
idempotency tests where relevant
```

### PERSISTENCE

Database schema, migrations, repositories, transaction behavior.

Required tests/checks:

```text
migration from empty database
repository round-trip tests
query/filter tests
transaction rollback tests
constraint tests
```

### API

HTTP/RPC routes, controllers, request/response mapping, auth/error handling.

Required tests/checks:

```text
route tests
request validation tests
response shape tests
status code tests
auth/error mapping tests
```

### CLI

Commands, flags, arguments, stdout/stderr, exit codes.

Required tests/checks:

```text
command parsing tests
required and optional argument tests
exit code tests
stdout/stderr tests
CLI integration tests
```

### UI

Screens, components, forms, UI state, accessibility, user journeys.

Required tests/checks:

```text
component tests
form validation tests
loading/empty/error state tests
accessibility checks
E2E happy path tests
```

### INTEGRATION_HARDENING

End-to-end validation, security, performance, docs, release readiness.

Required tests/checks:

```text
full unit suite
full integration suite
full E2E suite
lint/type/static checks
security checks where applicable
documentation checks
release smoke test
```

## SpecKit phase behavior

### specify

SpecKit receives the full HLD-derived input. It must not produce a partial spec for one implementation slice.

### plan

SpecKit creates one complete product plan. The plan must identify:

```text
MVP path
slice order
slice dependencies
test strategy per slice
adapter strategy: API / CLI / UI / persistence
HLD anchor coverage strategy
```

### tasks

SpecKit creates one complete task graph. Every task must include:

```text
task id
slice name
HLD anchor references
dependencies
expected files
focused test requirement
regression test requirement
MVP flag
stop condition
```

Example:

```text
T014
Slice: BUSINESS_LOGIC
MVP: true
HLD anchors: HLD-004, HLD-007
Depends on: DOMAIN_MODEL:T006, CONTRACTS:T011
Expected files: domain/services/*, tests/domain/*
Focused test: registration validation success/failure
Regression: domain + contracts tests
Forbidden: API routes, UI components, database migrations
```

### analyze

SpecKit or the reviewer verifies:

```text
every product task has HLD anchors
every task has a slice
every slice has tests
the MVP path is executable
no HLD anchor is silently dropped
dependencies are explicit
implementation has not started
```

### implement

Implementation is not run raw by default.

HLDspec must select:

```text
slice name
allowed task IDs
allowed files
forbidden files
required focused tests
required regression tests
anchors in scope
deferred anchors
stop condition
```

Example:

```text
Implement only slice: API
Allowed task IDs: T021, T022, T023
Forbidden: UI, new business rules, unrelated persistence changes
Run: API focused tests and all prior-slice regression tests
Write: phase_report.json and anchor_coverage.json
Stop.
```

## Slice completion rule

A slice is complete only when:

```text
focused tests pass
prior-slice regression passes
anchor coverage is updated
no uncited product behavior was added
phase_report.json is written
no stop condition is triggered
```

## Anchor coverage

Every HLD anchor must be accounted for after each slice:

```text
implemented
partially_implemented
deferred
blocked
not_applicable
```

No anchor may be silently omitted.

## Stop conditions

The implementation agent must stop if:

```text
required source files are missing
task lacks HLD anchors
selected slice is unclear
implementation touches forbidden files
tests fail
new product behavior is not cited to HLD
dependency requires unapproved future slice
human-owned decision appears
RunSkeptic returns ACTION or CONFLICT
```

## Summary

SpecKit plans the whole product once.

HLDspec controls implementation slice by slice by producing the slice contract,
allowed scope, required tests, and stop conditions. It does not hard-enforce the
slice at runtime; the user or Agent Mediator enforces the contract while the
implementation agent works.

## Artifact contract style for slices

Every slice is also a contract. A slice is not just a label like `API` or `UI`;
it must define the operational boundary for one implementation pass.

Required Slice card shape:

```text
Slice
Purpose
Inputs
Authority
Allowed work
Forbidden work
Expected outputs
Focused tests
Regression tests
Stop conditions
Report format
Next owner
Evidence
```

A slice that cannot name its allowed work, forbidden work, focused tests,
regression tests, and stop conditions is not ready for implementation.

See [HLDspec Artifact Contract Style](HLDSPEC_ARTIFACT_CONTRACT_STYLE.md).
