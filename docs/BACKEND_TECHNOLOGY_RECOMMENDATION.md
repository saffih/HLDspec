# Backend Technology Recommendation

## Purpose

This document defines HLDspec's short approved backend toolbox.

It is a guideline catalog, not a mandate. HLDspec chooses the simplest tool that satisfies the target project's forces.

Every upgrade from the default requires:

- named trigger
- reason
- complexity added
- tests required
- observability required
- rollback or simplification path
- RunSkeptic result

## Core rule

Use boring architecture by default.

Use stronger tools only when the HLD proves the force exists.

If unsure, run RunSkeptic.

## Short approved toolbox

| Category | Default | Upgrade | Trigger for upgrade |
|---|---|---|---|
| Architecture shape | Modular monolith | Microservices | Independent deployment, scaling, ownership, or fault isolation is proven |
| Domain structure | Clean architecture | Ports/adapters | External systems, DB, agents, queues, clocks, files, APIs, or test seams exist |
| State storage | SQLite or JSON state | Postgres | Multi-user, multi-worker, production durability, concurrency, migrations |
| Workflow model | Backend TEA state machine | Workflow engine | Long-running distributed workflows, timers, many retries, many workers |
| Resumability | Persistent loop | Event log | Need audit, replay-lite, stale detection, explainability, or agent trace |
| Communication | Direct calls | Message bus | Async, fan-out, retry, backpressure, or independent consumers |
| Consistency | DB transaction | Outbox/inbox | DB write and event/message publish must stay consistent |
| API contract | JSON Schema or OpenAPI | Contract tests | Producer/consumer boundary exists or external API exists |
| Testing | Unit + integration tests | E2E/contract tests | User-visible flow, API boundary, workflow, adapter, or message contract exists |
| Release safety | Normal deploy | Feature flags | Risky rollout, partial enablement, staged release, or rollback need |
| Observability | Structured logs | Metrics/tracing | Production, async work, workflow, performance, or debugging risk exists |
| Review gate | RunSkeptic | Human escalation | RunSkeptic finds CONFLICT or evidence is insufficient |
| Agent economy | Smallest context + weakest sufficient model | Strong/critical model | Architecture, source of truth, contract, dependency, security, or promotion gate |

## Backend TEA

Backend TEA is the default workflow model when workflow complexity exists.

Name:

```text
Persistent Command-Event State Machine
```

Formula:

```text
State + Message -> New State + Effects
```

Use when:

- workflow has phases
- approvals exist
- retries exist
- artifacts can become stale
- agents/tools execute steps
- resume after failure matters
- transitions must be valid

For HLDspec itself, Backend TEA is core.

For target products, Backend TEA is optional unless workflow/state complexity exists.

## SQLite or JSON state

Use SQLite or JSON state when:

- local tool
- prototype
- single-user workflow
- low concurrency
- simple durable state
- test fixture database
- no serious concurrent writes

Prefer JSON state only when the state is small, local, and easy to validate.

Prefer SQLite when state needs queries, transactions, or simple durable indexing.

## Postgres

Use Postgres when:

- production shared backend
- multiple users
- multiple workers
- concurrent writes
- durable workflow state
- migrations matter
- relational consistency matters
- reporting/querying matters
- the target product is expected to grow

## Message bus

Default to direct calls.

Use a message bus only when one of these forces exists:

- real async workflow
- fan-out to multiple consumers
- retry or backpressure is required
- producer and consumer must evolve independently
- event stream is part of audit or integration behavior

If using a message bus, require:

- event schema
- producer owner
- consumer owner
- ordering rule
- idempotency key
- retry policy
- dead-letter or failure handling
- observability
- contract tests

## Outbox/inbox

Outbox protects sending.

Inbox protects receiving.

Use outbox/inbox only when:

- there is message/event publishing
- a DB write and event publish must stay consistent
- duplicate messages are possible
- retries are expected
- lost or duplicated work is expensive

Default to a simple DB transaction when no message bus/event publishing exists.

## Workflow engine

Default to Backend TEA state machine plus persistent loop.

Upgrade to a workflow engine only when the workflow has:

- long-running distributed execution
- timers
- many retries
- many workers
- complex compensation
- operational need that exceeds a simple persistent loop

## Microservices

Default to modular monolith.

Upgrade to microservices only when independent deployment, scaling, ownership, or fault isolation is proven.

Microservices must not be selected just to appear modern.

## CQRS and event sourcing

CQRS and event sourcing are rare advanced options.

Use CQRS only when read and write models truly diverge.

Use event sourcing only when full historical reconstruction is a core requirement.

For most systems, use an event log instead of full event sourcing.

## Decision record required

Every selected upgrade must be recorded in:

```text
target/.hldspec/backend_technology_recommendation.md
target/.hldspec/backend_technology_recommendation.json
```

Required fields:

```text
category:
selected_tool:
default_or_upgrade:
trigger:
reason:
complexity_added:
tests_required:
observability_required:
rollback_or_simplification_path:
runskeptic_result:
```

## Acceptance criteria

A backend technology recommendation is valid when:

- every category has either the default or a justified upgrade
- every upgrade has a trigger
- testing impact is explicit
- observability impact is explicit
- rollback/simplification path is explicit
- RunSkeptic has reviewed risky choices
- no optional tool is selected without evidence
