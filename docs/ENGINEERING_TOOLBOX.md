# Engineering Toolbox

## Purpose

The Engineering Toolbox is HLDspec's reusable engineering doctrine for target
software. It helps target agents build software that is simple, flexible,
testable, observable, safe to evolve, and safe to test without corrupting the
user's active product or data.

The toolbox does not replace the HLD. The HLD says what the product should be.
The toolbox provides selected guidance for how to build it safely.

The Engineering Toolbox is protected by the anti-drift system. Contract 4 in
`docs/ANTI_DRIFT_CONTRACTS.md` is the non-droppable guardrail for this document:
future patches may improve the toolbox, but must not weaken, remove, rename, or scatter its protected clean-software, testability, and stage-safety concepts without an explicitly reviewed stronger replacement.

## Core rule

Mention principles by default. Expand only when a choice is unclear, risky,
tool-specific, or requires gate enforcement.

HLDspec must not copy the whole toolbox into every target. It selects only the
guidance needed for the current target, feature, phase, or risk.

## Terminology

- **Engineering Toolbox**: the global reusable catalog of principles and tool
  cards.
- **Engineering Principle**: a stable rule for healthy software, such as keeping
  business logic outside HTTP handlers or using contracts at boundaries.
- **Toolbox Card**: an opinionated implementation pattern with trigger,
  default choice, architecture shape, tests, forbidden shortcuts, evidence, and
  constitution/preferred-choice flags.
- **Principle Mention**: the shortest form of selected guidance. It names the
  principle without copying the full card.
- **Selected Guidance**: target-specific guidance with trigger, evidence,
  required tests, and enforcement expectation.
- **Full Card Expansion**: the complete Toolbox Card text. Use only when risk or
  ambiguity justifies the context cost.
- **Engineering Selection**: machine-readable selected principles/cards for a
  target or phase.
- **Engineering Guidelines**: generated human-readable guidance derived from the
  Engineering Selection and included in the source package.
- **Engineering Decision**: append-only record of selected defaults, upgrades,
  overrides, rejected options, and exceptions.
- **Constitution Candidate**: a durable engineering principle that may be
  proposed for the target SpecKit constitution after review.
- **Preferred Choice Selection**: a context-specific default selected from HLD
  or discussion triggers for SpecKit and implementation agents.

## Constitution candidates vs Preferred Choice Selection

The Engineering Toolbox produces two different kinds of output.

### Constitution candidates

Constitution candidates are stable, long-lived principles that should become
project law only after review and approval.

Examples:
- business logic must stay outside framework, transport, UI, CLI, and database
  adapters
- source-of-truth ownership must be explicit
- boundary contracts must be explicit
- behavior must be testable without production dependencies
- feature work must not mutate production or user-owned data without explicit
  approval

HLDspec must not silently overwrite the target constitution. It may propose a
constitution update, but approval is required.

### Preferred Choice Selection

Preferred Choice Selection is target-specific guidance selected from HLD or
discussion triggers. These are practical defaults for SpecKit and agents, not
permanent law.

Examples:
- API boundary exists -> prefer simple HTTP + JSON with DTOs/contracts
- CLI boundary exists -> require command boundary tests or golden tests
- UI boundary exists -> require UI tester skill on safe test/stage data
- persistence exists -> apply schema discipline
- shared mutable data exists -> prefer optimistic revision
- external systems exist -> use ports and adapters
- business rules exist -> isolate a business logic container and test it
  directly

## Guidance levels

### Level 1 - Principle Mention

Use when the principle is obvious and low-risk.

Example:

```text
Keep business logic outside HTTP handlers, controllers, framework containers,
UI components, CLI commands, and database adapters.
```

### Level 2 - Selected Guidance

Use when the principle affects the current target or phase and needs evidence or
tests.

Example:

```text
Orders are shared mutable records, so use revision-based optimistic updates and
prove stale updates do not overwrite newer changes.
```

### Level 3 - Full Toolbox Card

Use when a choice is risky, tool-specific, easy to get wrong, or gate-enforced.

Example:

```text
concurrency.optimistic_revision
- add a revision/version column
- update with WHERE id = ? AND revision = ?
- affected rows = 0 means conflict/reload/merge
- test two actors reading the same revision
```

## Artifact layout

Global catalog:

```text
docs/
  ENGINEERING_TOOLBOX.md
  engineering_toolbox/
    cards/
      api-http-json.md
      data-schema.md
      concurrency-optimistic-revision.md
```

Target selection and decision state:

```text
target/.hldspec/engineering/
  selection.json
  decisions.jsonl
```

Source package guidance:

```text
target/.hldspec/source_package/
  engineering_guidelines.md
```

SpecKit mirror:

```text
target/.specify/source/
  engineering_guidelines.md
```

Do not create duplicate human-readable engineering guidance files. The target
markdown guidance lives in `engineering_guidelines.md`; the selected machine
truth lives in `selection.json`.

## Toolbox card format

Every full Toolbox Card must use this shape:

```text
### card.id

Trigger:
- when this card is selected

Default choice:
- the preferred engineering choice

Required architecture shape:
- what the target architecture must expose

Required tests:
- focused tests, contract tests, UI tests, stage-safety tests, or regressions

Forbidden shortcuts:
- what agents must not do

Evidence required:
- what phase reports, test output, or artifacts must show

Constitution candidate:
- yes/no

Preferred choice:
- yes/no
```

## P0 cards

P0 proves the enforcement loop with a small but non-trivial set of clean
software cards.

### api.http_json

Trigger:
- an HTTP API, client boundary, public API, multi-client API, or service
  boundary exists.

Default choice:
- Default to simple HTTP + JSON with explicit DTOs/contracts and a small
  endpoint surface.
- Use OpenAPI or JSON Schema when a client boundary, multi-client API, or
  public API exists.
- Do not default to hypermedia/HATEOAS unless runtime-discovered transitions are
  a real product need.

Required architecture shape:
- HTTP handlers translate transport concerns and call the business logic
  container.
- DTOs/contracts live at the boundary.
- Domain/application behavior does not live in handlers.

Required tests:
- handler/contract tests for boundary shape
- business logic tests below the HTTP layer
- negative tests for invalid input and errors

Forbidden shortcuts:
- hiding business rules in handlers
- accepting untyped/raw payloads as domain objects
- using endpoint tests as the only proof of business behavior

Evidence required:
- contract files or explicit DTOs
- focused tests proving validation and business behavior

Constitution candidate:
- yes, as "explicit contracts at system boundaries"

Preferred choice:
- yes

### data.schema_discipline

Trigger:
- persistent entities, migrations, indexes, uniqueness, joins, or business
  records exist.

Default choice:
- Use stable primary keys.
- Use foreign keys where database-enforced integrity matters.
- Use unique constraints for business uniqueness.
- Add indexes for named query paths, joins, ordering, pagination, or uniqueness.
- Do not add speculative indexes.
- Use JSON columns only for truly flexible or raw payload-shaped data; if a JSON
  field becomes queried, constrained, joined, or business-critical, promote it to
  typed schema.

Required architecture shape:
- persistence concerns stay behind repositories/adapters/ports
- schema choices are documented as selected guidance or decisions

Required tests:
- persistence integration tests on disposable test DBs or fixtures
- uniqueness and integrity negative tests
- migration smoke where migrations exist

Forbidden shortcuts:
- storing core typed business data as opaque JSON because it is faster
- running schema-changing tests against production or user-owned data
- adding indexes without named query evidence

Evidence required:
- schema/migration file
- tests or migration smoke output
- reason for non-obvious schema choices

Constitution candidate:
- yes, as "source-of-truth and data integrity must be explicit"

Preferred choice:
- yes

### concurrency.optimistic_revision

Trigger:
- shared mutable records can be edited by more than one actor, process, request,
  agent, or UI session.

Default choice:
- Default to optimistic revision updates for shared mutable records.

```sql
UPDATE table_name
SET field = ?, revision = revision + 1
WHERE id = ? AND revision = ?;
```

If affected rows is `0`, treat it as conflict, reload, merge, or retry according
to a declared policy. Do not default to broad locking or `SELECT FOR UPDATE`.
Locks are a narrow exception for short critical sections where optimistic
conflict handling is not acceptable.

Required architecture shape:
- revision/version field or equivalent conflict token
- explicit conflict handling path
- business logic container owns conflict semantics

Required tests:
- two actors reading the same revision
- first update succeeds
- stale second update fails or resolves according to policy
- no silent overwrite

Forbidden shortcuts:
- last-write-wins without explicit product decision
- hidden broad locks as a default
- conflict policy only in UI with no domain/application test

Evidence required:
- revision update code
- stale-write focused test
- phase report naming the conflict policy

Constitution candidate:
- no, except as part of source-of-truth integrity

Preferred choice:
- yes

### architecture.hexagonal_ports_adapters

Trigger:
- the product has API, CLI, UI, persistence, external integration, replaceable
  infrastructure, or meaningful business behavior.

Default choice:
- Use hexagonal architecture / ports and adapters.
- Domain and application code define the core behavior and ports.
- HTTP, CLI, UI, database, filesystem, queues, clocks, ID generation, and
  external SDKs are adapters.

Required architecture shape:
- business logic does not depend on frameworks, transports, or infrastructure
- ports/interfaces describe what the core needs
- adapters translate external concerns into core calls

Required tests:
- core behavior tests through the business logic container and ports
- adapter tests for each real boundary
- contract tests where external/client boundaries exist

Forbidden shortcuts:
- placing business rules in controllers, handlers, UI components, database
  adapters, or SDK wrappers
- letting external tools shape the domain model
- requiring a server/UI/database to test core rules

Evidence required:
- visible core/application boundary
- tests proving core behavior without production services
- adapter tests or contracts

Constitution candidate:
- yes

Preferred choice:
- yes

### architecture.business_logic_container

Trigger:
- the product has business rules, workflows, decisions, validation, state
  transitions, permissions, pricing, scheduling, or domain behavior.

Default choice:
- Put business logic in a fully testable business logic container, such as an
  application service, use-case layer, domain service, or domain model.
- HTTP handlers, CLI commands, UI actions, jobs, and DB adapters call into it.

Required architecture shape:
- one clear entry point for each use case/workflow
- injected dependencies or ports for time, IDs, persistence, external APIs,
  filesystem, network, and randomness
- no dependency on production services for focused behavior tests

Required tests:
- focused business logic tests for every business rule
- negative/edge-case tests
- regression tests for prior bugs or known risky paths

Forbidden shortcuts:
- testing business rules only through UI or HTTP smoke tests
- hiding use-case logic in framework callbacks
- using real production state in focused tests

Evidence required:
- business logic container exists
- focused tests cover rules, errors, and edge cases

Constitution candidate:
- yes

Preferred choice:
- yes

### architecture.modular_boundaries

Trigger:
- the product has multiple domains, features, actors, bounded contexts, or likely
  future change pressure.

Default choice:
- Prefer modular monolith/internal modules before services unless deployment,
  scaling, ownership, security, or runtime isolation boundaries are real.
- Each module declares ownership, inputs, outputs, contracts, and persistence
  boundary.

Required architecture shape:
- clear module boundaries
- no accidental cross-module data ownership
- interfaces/contracts for important cross-module calls

Required tests:
- module-level behavior tests
- contract tests for cross-module boundaries when needed

Forbidden shortcuts:
- splitting into services only for style
- direct database sharing across ownership boundaries without explicit reason
- circular module dependencies

Evidence required:
- module boundary description
- tests or contracts for cross-boundary behavior

Constitution candidate:
- no, unless the target needs long-lived modularity law

Preferred choice:
- yes

### testing.design_for_testability

Trigger:
- any non-trivial business behavior, external dependency, async flow, UI, CLI,
  persistence, time/ID/randomness, or integration exists.

Default choice:
- Design for testability from the start.
- Dependencies must be injectable or replaceable.
- Time, IDs, randomness, external APIs, filesystem, network, queues, and
  production services must be controllable in tests.

Required architecture shape:
- business logic container accepts ports/dependencies
- adapters are replaceable with fakes/stubs/test doubles
- configuration separates test/stage/prod

Required tests:
- focused unit/application tests without production dependencies
- integration tests only where boundary behavior requires them
- deterministic tests for time/ID/randomness-sensitive logic

Forbidden shortcuts:
- using production config in tests
- requiring a live UI/server/database for every business rule test
- writing tests that pass only by depending on real time, real network, or real
  production data

Evidence required:
- injectable dependency seams
- deterministic focused test output
- explicit test/stage config

Constitution candidate:
- yes

Preferred choice:
- yes

### testing.business_logic_coverage

Trigger:
- business rules, workflows, domain decisions, state transitions, permissions,
  pricing, scheduling, validation, or risk-bearing logic exists.

Default choice:
- Every business rule must have focused unit/domain/application tests.
- Handler/UI/E2E tests are not a substitute for business logic tests.

Required architecture shape:
- business logic can be called directly below transport/UI
- rule inputs and outputs are observable in tests

Required tests:
- positive case
- negative case
- edge case
- stale/regression case when relevant

Forbidden shortcuts:
- relying only on UI automation or manual QA for domain behavior
- adding logic without tests because it is "small"
- testing only happy paths

Evidence required:
- focused test names or report entries tied to rules

Constitution candidate:
- yes

Preferred choice:
- yes

### testing.contract_boundary

Trigger:
- public API, CLI, UI workflow, external integration, file format, event payload,
  data import/export, or client boundary exists.

Default choice:
- Boundary behavior must be covered by contract tests, golden tests, schema
  checks, or equivalent stable fixtures.

Required architecture shape:
- boundary shape is explicit
- payloads/commands/events/errors are documented or schema-backed

Required tests:
- valid contract example
- invalid contract example
- backward compatibility or migration test when relevant

Forbidden shortcuts:
- undocumented payload changes
- changing CLI/API/UI-visible behavior without contract/golden update
- treating adapter mocks as proof of public contract

Evidence required:
- contract/golden/schema test output
- changed contract reviewed when behavior changes

Constitution candidate:
- yes, as boundary contract discipline

Preferred choice:
- yes

### testing.ui_tester_skill

Trigger:
- user-visible UI exists or a feature changes UI behavior, layout, forms,
  navigation, accessibility, errors, empty states, or regressions.

Default choice:
- Use a UI tester skill or equivalent UI validation workflow against test/stage
  data.
- UI tests must verify user-visible flows, errors, empty states, and regressions.

Required architecture shape:
- UI can point to test/stage backend or fixture data
- UI test setup does not mutate production/user-owned data
- business logic remains testable below UI

Required tests:
- happy path
- error path
- empty/loading state where relevant
- regression/golden/screenshot/accessibility check where relevant

Forbidden shortcuts:
- claiming UI is tested because backend tests pass
- running UI automation against production/user-owned data
- embedding business rules only in UI components

Evidence required:
- UI tester report or command output
- environment used
- data safety statement

Constitution candidate:
- no, unless UI safety is a permanent project rule

Preferred choice:
- yes

### environment.stage_safe_testing

Trigger:
- feature work can write, delete, migrate, seed, import, export, automate UI, call
  external systems, or otherwise mutate state.

Default choice:
- Feature work must not corrupt the user's active product or data.
- Implementation and tests must run in an isolated test/stage workspace.
- Production or user-owned data requires explicit approval before mutation.

Required architecture shape:
- clear test/stage/prod labels
- safe test/stage environment boundaries
- disposable workspace, temp dir, test DB, seeded fixtures, or isolated service
- safe cleanup/reset path

Required tests:
- smoke proves generated artifacts stay under target/temp root when applicable
- destructive flows use disposable state
- migration tests use test DB or explicit dry-run

Forbidden shortcuts:
- running migrations/deletes/seeds/UI automation against production by default
- using the user's active workspace as a destructive test target
- hiding environment assumptions in shell history or local config

Evidence required:
- environment name
- target path
- reset/cleanup method
- explicit approval when touching production or user-owned data

Constitution candidate:
- yes

Preferred choice:
- yes

### environment.prod_test_separation

Trigger:
- there is any persistent data, external service, deployment environment, UI
  automation, migration, destructive operation, or user-owned workspace.

Default choice:
- Test, stage, and production data/config must be separated.
- Destructive tests require throwaway targets, temp dirs, test DBs, mocked
  external services, or seeded fixtures.
- No feature agent may run migrations, deletes, writes, imports, exports, or UI automation against production unless explicitly approved.

Required architecture shape:
- environment-specific config
- no shared production credentials in test workflow
- test/stage data isolation

Required tests:
- environment guard test or dry-run check where possible
- smoke showing test target isolation for generated artifacts
- reset path for fixtures/state

Forbidden shortcuts:
- defaulting to production config
- using real customer/user data in automation
- running destructive tests without a reset strategy

Evidence required:
- environment labels in reports
- commands or config proving test/stage target
- approval evidence for any production mutation

Constitution candidate:
- yes

Preferred choice:
- yes

### testing.resettable_fixtures

Trigger:
- tests use persistent state, UI flows, e2e flows, external services, generated
  files, or seeded data.

Default choice:
- Tests need deterministic seed/reset strategy.
- E2E and UI tests must clean up or use isolated disposable state.

Required architecture shape:
- fixture seed and cleanup entry points
- test data namespacing or disposable resources
- no dependency on execution order

Required tests:
- repeated run passes
- cleanup/reset works
- test data does not leak into production/user data

Forbidden shortcuts:
- manual fixture cleanup
- order-dependent tests
- shared mutable test state without reset

Evidence required:
- seed/reset command or fixture code
- repeated-run result or cleanup statement

Constitution candidate:
- no

Preferred choice:
- yes

## Trigger mapping

HLD Discussion and future Engineering Toolbox Selection should map these triggers
to cards:

| Trigger | Select |
|---|---|
| `api_boundary` | `api.http_json`, `testing.contract_boundary`, `architecture.business_logic_container` |
| `cli_boundary` | `testing.contract_boundary`, `architecture.business_logic_container` |
| `ui_boundary` | `testing.ui_tester_skill`, `architecture.business_logic_container`, `environment.stage_safe_testing` |
| `persistence` | `data.schema_discipline`, `environment.prod_test_separation`, `testing.resettable_fixtures` |
| `external_integration` | `architecture.hexagonal_ports_adapters`, `testing.contract_boundary`, `environment.stage_safe_testing` |
| `shared_mutable_data` | `concurrency.optimistic_revision`, `testing.business_logic_coverage` |
| `source_of_truth_ambiguity` | `data.schema_discipline`, `architecture.modular_boundaries` |
| `business_rules` | `architecture.business_logic_container`, `testing.business_logic_coverage`, `testing.design_for_testability` |
| `testability_risk` | `testing.design_for_testability`, `testing.resettable_fixtures` |
| `ui_testing_needed` | `testing.ui_tester_skill`, `environment.stage_safe_testing` |
| `stage_safe_testing_needed` | `environment.stage_safe_testing`, `environment.prod_test_separation` |
| `prod_test_separation_needed` | `environment.prod_test_separation` |
| `destructive_operation_risk` | `environment.stage_safe_testing`, `environment.prod_test_separation`, `testing.resettable_fixtures` |
| `migration_or_schema_change` | `data.schema_discipline`, `environment.prod_test_separation`, `testing.resettable_fixtures` |
| `async_or_message_bus_candidate` | `architecture.hexagonal_ports_adapters`, `testing.contract_boundary` |

## Agent use rule

Agents must not treat the Engineering Toolbox as optional when selected guidance
exists.

When `target/.hldspec/source_package/engineering_guidelines.md` or
`target/.specify/source/engineering_guidelines.md` exists, SpecKit agents,
implementation agents, and mediators must read it before planning or
implementation work. These files are required guidance when present, not
optional context. They must report selected cards, evidence produced, and any
selected guidance they could not satisfy.

## Enforcement loop

P0 is complete only when this loop is proven:

```text
selected card
  -> generated engineering_guidelines.md
  -> target AGENTS / runner prompt requirement
  -> implementation or phase-report evidence
  -> gate blocks missing evidence
  -> gate passes with evidence
```

The catalog itself is not the product. The selected, enforced target guidance is
the product behavior.

Status: minimal P0 `engineering_guidelines.md` generation is implemented. Every new source package build generates a real, target-specific `engineering_guidelines.md` (and its `.specify/source/` mirror) from the always-on baseline cards plus the P0 cards triggered by the HLD (`hldspec/engineering_selection.py`).

This is P0-card selected guidance, not the full enforcement loop. The machine-readable `selection.json` / `decisions.jsonl` records and the gate that blocks missing card evidence are still future work. HLDspec must not copy the whole toolbox into every target: generation stays limited to selected and baseline P0 cards.

## Gate flags

Mark ACTION or block when:

- selected guidance has no trigger or target evidence
- risky tool upgrade has no tests, observability, or rollback path
- implementation uses an unselected risky pattern
- behavior changes without a provisional source-truth delta
- mutable shared writes lack optimistic revision or explicit single-writer rule
- API boundary lacks DTO/schema/contract strategy
- business rules are not covered by focused business logic tests
- UI changes have no UI tester skill evidence when UI testing is selected
- cache exists without owner, TTL, invalidation, stale-read tolerance, and
  fallback
- schema/index/foreign-key/JSON choice has no reason
- selected card requirements are absent from tests or reports
- feature work mutates production or user-owned data without explicit approval

## Relationship to constitution

Stable principles may be proposed for the target constitution. Feature-specific
or phase-specific choices should stay in engineering selection, spec inputs,
prompts, reports, or provisional change records.

The constitution should not become a toolbox dump.
