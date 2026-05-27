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

`.specify/source/` is generated read-only context for SpecKit. It is not the source of truth.

## Why slices exist

SpecKit can create a complete plan and task graph for the full product. But implementation may be too large or risky to run in one pass.

Slice control lets HLDspec say:

```text
The full product is known.
The full task graph is known.
Only this selected part may be implemented now.
```

## Canonical slices

### FOUNDATION

Workspace setup, build/test commands, project scaffold, and SpecKit initialization validation.

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

Entities, value objects, statuses, invariants, and domain errors.

Must not depend on database, API, CLI, UI, or network.

Required tests/checks:

```text
entity creation tests
value object validation tests
invalid state rejection tests
status transition tests
```

### CONTRACTS

Ports, interfaces, DTOs, schemas, and API/event contracts.

Required tests/checks:

```text
schema validation tests
DTO shape tests
port contract tests
invalid payload tests
```

### BUSINESS_LOGIC

Use cases, workflows, validation rules, and state transitions.

Required tests/checks:

```text
use-case tests
workflow tests
business rule tests
error-path tests
idempotency tests where relevant
```

### PERSISTENCE

Database schema, migrations, repositories, and transaction behavior.

Required tests/checks:

```text
migration from empty database
repository round-trip tests
query/filter tests
transaction rollback tests
constraint tests
```

### API

HTTP/RPC routes, controllers, request/response mapping, auth, and error handling.

Required tests/checks:

```text
route tests
request validation tests
response shape tests
status code tests
auth and error mapping tests
```

### CLI

Commands, flags, arguments, stdout/stderr, and exit codes.

Required tests/checks:

```text
command parsing tests
required and optional argument tests
exit code tests
stdout/stderr tests
CLI integration tests
```

### UI

Screens, components, forms, UI state, accessibility, and user journeys.

Required tests/checks:

```text
component tests
form validation tests
loading, empty, and error state tests
accessibility checks
E2E happy path tests
```

### INTEGRATION_HARDENING

End-to-end validation, security, performance, docs, and release readiness.

Required tests/checks:

```text
full unit suite
full integration suite
full E2E suite
lint, type, and static checks
security checks where applicable
documentation checks
release smoke test
```

## SpecKit phase behavior

### specify

SpecKit receives the full HLD-derived input.

It must not produce a partial spec for one slice.

### plan

SpecKit creates one complete product plan.

The plan must identify:

```text
MVP path
slice order
slice dependencies
test strategy per slice
adapter strategy: API, CLI, UI, persistence
HLD anchor coverage strategy
```

### tasks

SpecKit creates one complete task graph.

Every task must include:

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
Expected files: hldspec/domain/*, tests/domain/*
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
phase report is written
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
dependency requires an unapproved future slice
human-owned decision appears
RunSkeptic returns ACTION or CONFLICT
```

## Summary

SpecKit plans the whole product once.

HLDspec controls implementation slice by slice.
