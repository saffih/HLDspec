# Software Design Principles for HLDspec

## Purpose

This document is HLDspec's reusable software design knowledge base.

It helps HLDspec build or improve HLDs, extract target constitutions, slice HLDs into SpecKit-ready packages, generate prompts, and run RunSkeptic at the right junctions.

These principles are global HLDspec knowledge. Target-specific rules are extracted from them into `target/.hldspec/constitution_update_plan.*` and, after approval, into `target/.specify/memory/constitution.md`.

## Use in HLDspec

HLDspec must use these principles when it:

- builds or improves `target/targetHLD/HLD.md`
- groups HLD sections
- extracts constitution signals
- slices spec packages
- builds dependency graphs
- generates SpecKit prompts
- generates mediator prompts
- evaluates testability
- reviews architecture decisions
- runs or requests RunSkeptic

## Priority rules

1. Do not invent architecture.
2. Preserve source-of-truth evidence.
3. Prefer simple explicit designs over clever implicit designs.
4. Prefer small bounded packages over broad vague packages.
5. Prefer interfaces and contracts over hidden coupling.
6. Prefer deterministic tests over fragile test setups.
7. Prefer observable resumable workflows over hidden state.
8. Prefer weakest sufficient model and smallest sufficient context.
9. Use RunSkeptic when risk, uncertainty, conflict, or architectural impact exists.
10. Stop and escalate human-owned decisions.

## Source of truth

Every important fact must have an owner and source.

Rules:

- Define the canonical source for requirements, architecture, data, APIs, configuration, and generated artifacts.
- Do not allow multiple competing sources of truth without an explicit reconciliation rule.
- Generated artifacts must declare their source inputs where possible.
- If source evidence conflicts, mark CONFLICT and run RunSkeptic.
- If evidence is missing, mark TBD or ACTION. Do not silently guess.

## Interfaces and contracts

Boundaries must be explicit.

Use interfaces/contracts for:

- API boundaries
- component boundaries
- persistence boundaries
- message/event boundaries
- external services
- UI-to-backend seams
- test doubles
- infrastructure adapters

A contract should define:

- producer
- consumer
- request or event schema
- response or result schema
- ownership
- versioning
- error behavior
- timeout behavior
- retry behavior
- test strategy

## Clean architecture

HLDspec should prefer designs where business rules do not depend on infrastructure details.

Rules:

- Keep domain logic separate from framework, database, UI, and transport code.
- Depend on abstractions where the dependency crosses a boundary.
- Use dependency injection for replaceable dependencies.
- Keep side effects at the edges.
- Avoid hidden global state.
- Keep modules small and owned.
- Make data ownership explicit.
- Do not introduce layers unless they reduce real coupling or improve testability.

## Ports and adapters

Use ports/adapters when a dependency must be replaceable, testable, or isolated.

Good candidates:

- database access
- message bus
- external APIs
- file systems
- clocks
- random generators
- authentication providers
- notification providers
- UI drivers
- CLI or shell execution
- SpecKit/agent invocation

Each port should include:

- purpose
- methods or messages
- ownership
- failure behavior
- test double strategy
- integration test plan

## Message-bus and event-driven style

Message bus, event log, or queue style can reduce coupling when components need asynchronous communication or independent evolution.

Use it when it solves a real force:

- producer and consumer should not block each other
- multiple consumers need the same fact
- workflow needs retry or resume
- external systems are unreliable
- events are useful audit/history records
- ordering and idempotency can be defined

Do not use it just to appear decoupled.

Required design points:

- event name and version
- producer owner
- consumer owners
- schema
- ordering guarantee
- idempotency key
- retry policy
- dead-letter or failure handling
- observability
- replay or recovery behavior
- contract tests

## State machines

Use state machines for workflows with gates, retries, or resumability.

A state machine should define:

- states
- allowed transitions
- transition owner
- input message
- output command
- artifacts read
- artifacts written
- failure mode
- recovery action

HLDspec itself should prefer this model:

```text
State + Message -> New State + Commands
```

## Persistent loop and resumability

Long-running or multi-agent work needs durable progress.

Use a persistent loop when work must survive interruption, agent failure, or partial completion.

Required design points:

- durable state file or event log
- idempotent step execution
- explicit step status
- stale artifact detection
- resume command
- stop condition
- retry policy
- maximum retry or escalation rule
- human checkpoint for ambiguous decisions

Avoid hidden in-memory progress as the only control state.

## Design for testability

Testability is a design requirement, not a final cleanup step.

Each HLD section and spec package should identify:

- unit test seams
- integration test seams
- end-to-end testability path
- external dependencies
- mocks, fakes, stubs, or spies
- deterministic controls for time, random, I/O, and network
- fixtures or test data builders
- missing test tools or harnesses

If testability is unclear, mark ACTION and run RunSkeptic.

## Unit testing

Unit tests should cover domain logic, decision logic, validators, contracts, state transitions, and failure handling.

Rules:

- Keep unit tests deterministic.
- Avoid real network, clock, random, and filesystem unless the unit is specifically about that boundary.
- Prefer table-driven or scenario-based tests where useful.
- Include happy path, edge cases, and error cases.
- Test state transitions explicitly.
- Test idempotency where retries are possible.

## Integration testing

Integration tests should prove ports, adapters, persistence, contracts, and service boundaries.

Rules:

- Use realistic infrastructure when the adapter is the unit under test.
- Keep fixtures isolated.
- Avoid shared mutable test state.
- Test migrations or schema changes when relevant.
- Test message/event compatibility when using bus or queue style.
- Test retry and failure paths for external dependencies.

## End-to-end and accessibility testing

End-to-end tests should prove the user-visible or system-visible flow works through the real integration path.

When UI, CLI, API, or user workflow is involved, packages should define:

- e2e path
- scenario data
- success criteria
- failure criteria
- observability needed to debug failure
- accessibility checks where UI is user-facing

Accessibility must be treated as a quality requirement for user-facing UI.

Consider:

- keyboard navigation
- screen reader labels
- color contrast
- focus order
- error message clarity
- reduced motion where relevant
- semantic structure

## QA tooling and test harnesses

Every package must say how it will be tested.

If required tooling does not exist, the package must either:

- create the approved harness as part of the work, or
- stop and request approval

Examples of tooling:

- unit test runner
- integration test runner
- e2e or UI test tool
- contract test tool
- fixture/test data generator
- local environment runner
- CI job
- smoke test command
- regression test command

## Quality gates

Quality gates should exist at key transitions.

Common gates:

- HLD generated
- target workspace created
- constitution signals extracted
- constitution update plan created
- spec packages sliced
- dependency graph created
- SpecKit prompt generated
- SpecKit specify complete
- SpecKit plan complete
- SpecKit tasks complete
- implementation approval requested
- implementation complete
- merge/release readiness

Each gate should define:

- required artifacts
- required checks
- RunSkeptic trigger
- pass/fix/conflict outcomes
- owner
- next allowed action

## Security and reliability

Security and reliability must be explicit for relevant systems.

Rules:

- Validate inputs at boundaries.
- Do not leak secrets in logs or errors.
- Do not store secrets in code or generated docs.
- Define timeout behavior.
- Define retry behavior.
- Define graceful degradation where needed.
- Define rollback or recovery path.
- Make destructive operations explicit and gated.
- Log enough context to debug without exposing sensitive data.

## Performance and scalability

Performance requirements must be measurable where possible.

Rules:

- Define latency, throughput, memory, storage, or concurrency expectations when relevant.
- Identify expensive paths.
- Avoid hidden unbounded loops.
- Define backpressure for queues or message bus designs.
- Define load or stress validation when performance matters.
- Treat missing performance evidence as ACTION, not PASS.

## Configuration and environments

Configuration must be explicit and testable.

Rules:

- Define config source priority.
- Separate dev/test/staging/production where relevant.
- Keep test data isolated from production data.
- Support staging validation before production promotion.
- Define rollback and recovery for deployment changes.
- Do not rely on hidden local machine state.

## Cost and context economy

HLDspec must protect cost, context size, and agent attention.

Rules:

- Use the smallest sufficient context.
- Use the weakest sufficient agent/model.
- Use the narrowest sufficient prompt.
- Prefer deterministic scripts for mechanical extraction and validation.
- Preload relevant HLD knowledge into prompts.
- Do not reread a huge HLD unless explicitly needed.
- Give subagents one feature, one phase, or one bounded check.
- Use stronger models only for architecture, source of truth, contracts, conflict resolution, promotion gates, or high-risk implementation.

Cost/context economy is a correctness principle because overloaded agents miss constraints, confuse sources, and produce broad low-quality work.

## RunSkeptic at key junctions

RunSkeptic is a core execution mechanism.

Use RunSkeptic at key junctions and whenever uncertain.

Required trigger points:

- HLD generation or improvement
- target workspace creation
- HLD grouping
- constitution signal extraction
- constitution update plan
- spec package slicing
- dependency graph generation
- SpecKit invocation queue
- delegation prompt generation
- SpecKit phase promotion
- implementation approval
- post-implementation verification
- merge/release readiness

If in doubt, run or apply RunSkeptic.

Outcomes:

- PASS: continue
- ACTION: fix and rerun the relevant gate
- CONFLICT: stop and escalate

Missing evidence is ACTION or CONFLICT, not PASS.

## Prompt integration

Generated prompts must include only the principles relevant to the phase.

Every target-agent prompt should include:

- allowed evidence
- forbidden broad reads
- model tier
- max scope
- RunSkeptic triggers
- test expectations
- stop condition
- escalation rule

## Constitution integration

The target constitution must extract durable, target-specific rules from this document and the target HLD.

The constitution must remain principle-level.

It must not include:

- feature ids
- feature names
- feature order
- branch names
- implementation task ids
- per-feature implementation details

## Backend technology recommendation

Use `docs/BACKEND_TECHNOLOGY_RECOMMENDATION.md` as the short approved backend toolbox.

HLDspec must not select every architecture pattern. It must select the smallest useful set for the target project.

Every optional upgrade must document:

- trigger
- reason
- complexity added
- tests required
- observability required
- rollback or simplification path
- RunSkeptic result

If a tool is selected without a trigger, mark ACTION and block promotion.
