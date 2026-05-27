# HLDspec

HLDspec is an agent-first control layer for turning a full HLD into a safe, traceable SpecKit execution workflow.

It does not replace SpecKit. It prepares product truth, validates evidence, gates decisions, and tells SpecKit or a build agent exactly what to do next, what to read, what not to touch, what tests to run, and when to stop.

## The problem HLDspec solves

Large HLDs are too dense for one-shot implementation. If an agent slices the HLD manually, it can lose requirements, invent missing product truth, duplicate logic across layers, or implement too much at once.

HLDspec solves this by keeping the full HLD intact while controlling execution:

```text
One complete HLD
One HLDspec source package
One SpecKit workspace
One complete specify -> plan -> tasks -> analyze flow
Many approved implementation slices
```

The HLD remains the source of truth. The implementation is sliced, not the truth.

## What HLDspec is

HLDspec is:

- a source-truth preparation system for HLD-driven projects
- a target-workspace controller
- a gate and review system
- a SpecKit handoff generator
- a bounded-agent orchestration model
- a traceability and reassessment loop

HLDspec is not:

- a replacement for SpecKit
- a tool for hand-writing final SpecKit specs
- an implementation agent
- a silent product-decision owner
- a system that splits product truth into partial specs by default

## Core ownership model

| Owner | Owns |
|---|---|
| Human decision owner | Intent, product/architecture decisions, source-of-truth changes, risky approvals |
| HLDspec | HLD source package, gates, validation, prompts, run cards, reassessment |
| SpecKit | Constitution, final spec, plan, tasks, implementation artifacts |
| Build agent / SpecKit proxy | Executes only the bounded run card or slice prompt |

HLDspec can prepare and constrain work. It cannot silently approve human-owned decisions.

## Target workspace layout

A target workspace has two important areas:

```text
target/
  .hldspec/
    source_package/
      HLD.md
      HLD.marked.md
      hld_reference_map.json
      speckit_single_spec_input.md
      implementation_slices.json
      slice_execution_policy.md
      source_manifest.json
      source_package.json
      session_plan.json
      speckit_runbook.md

  .specify/
    source/
      generated read-only mirror of selected .hldspec/source_package files
    memory/
      constitution.md       # SpecKit-owned when initialized

  specs/
    ...                     # SpecKit-owned final spec artifacts
```

Rules:

- `.hldspec/source_package/` is the HLDspec source package.
- `.specify/source/` is a generated read-only mirror for SpecKit context.
- `.specify/memory/` and `specs/` are SpecKit-owned.
- Source HLD evidence is preserved; HLDspec works from controlled workspace copies.

## Conceptual flow

```mermaid
flowchart TD
    A[Human intent + source HLD] --> B[HLDspec start]
    B --> C[Capture source truth]
    C --> D[Build .hldspec/source_package]
    D --> E[Mirror read-only context to .specify/source]
    E --> F[Initialize or validate SpecKit workspace]
    F --> G[/speckit.specify once]
    G --> H[/speckit.plan once]
    H --> I[/speckit.tasks once]
    I --> J[/speckit.analyze once]
    J --> K{Implementation approved?}
    K -- no --> L[Stop for review or human decision]
    K -- yes --> M[Select implementation slice + task IDs]
    M --> N[Run bounded implementation pass]
    N --> O[Run focused tests + prior regression]
    O --> P[Write phase report + anchor coverage]
    P --> Q[HLDspec reassessment]
    Q --> R{More approved slices?}
    R -- yes --> M
    R -- no --> S[Final hardening or release gate]
```

## Process in plain language

1. The user provides a full HLD and a target workspace.
2. HLDspec copies and normalizes the HLD into controlled workspace evidence.
3. HLDspec marks HLD sections with stable anchors such as `HLD-001`.
4. HLDspec builds a source package and a single SpecKit input from the full HLD.
5. HLDspec mirrors read-only source context into `.specify/source/`.
6. SpecKit creates the full product spec, plan, task graph, and analysis.
7. HLDspec does not allow raw all-task implementation by default.
8. HLDspec selects one approved implementation slice and task list.
9. The build agent implements only that selected slice.
10. The build agent runs focused tests and prior-slice regression.
11. The build agent reports back with changed files, test evidence, anchor coverage, and blockers.
12. HLDspec reassesses and decides the next safe action.

## Slice-controlled implementation

HLDspec keeps one complete HLD and one complete SpecKit task graph. It controls implementation through named slices.

Canonical slices:

| Slice | Purpose | Typical validation |
|---|---|---|
| FOUNDATION | Workspace, scaffold, build/test commands, SpecKit init validation | build/test command exists and runs |
| WALKING_SKELETON | Minimal runnable path with placeholders | app starts, one smoke path works |
| DOMAIN_MODEL | Entities, value objects, statuses, invariants | pure domain unit tests and invalid-state tests |
| CONTRACTS | Ports, DTOs, schemas, event/API contracts | schema/DTO/port contract tests |
| BUSINESS_LOGIC | Use cases, workflows, validation rules | focused use-case and error-path tests |
| PERSISTENCE | DB schema, migrations, repositories | migration, round-trip, transaction tests |
| API | HTTP/RPC routes, controllers, request/response mapping | route, status, auth, error mapping tests |
| CLI | Commands, args, flags, output, exit codes | command parsing and CLI integration tests |
| UI | Screens, components, forms, user journeys | component, form, accessibility, E2E tests |
| INTEGRATION_HARDENING | End-to-end, security, performance, docs, release checks | full regression and release smoke |

Each implementation pass must name:

- selected slice
- allowed task IDs
- HLD anchors in scope
- deferred anchors
- allowed files
- forbidden files
- focused tests
- prior-slice regression tests
- stop condition

A slice is not complete because files changed. It is complete only when tests pass, anchor coverage is updated, and the phase report is written.

See `docs/SPECKIT_SLICE_CONTROL.md` for the technical contract.

## Gates and stop conditions

HLDspec blocks continuation when required evidence is missing, validation fails, anchors are stale, unsupported claims appear, RunSkeptic returns ACTION or CONFLICT, consultant review is missing, or human approval is required.

Agents must stop when:

- they need to make a source-of-truth decision
- they need to answer a human-owned architecture/product question
- selected slice or task IDs are unclear
- they must touch forbidden files
- tests fail
- a required HLD anchor is missing
- implementation would add uncited product behavior
- they cannot prove the next action is safe

## Main user workflow

The public facade is intentionally small:

```bash
python3 scripts/hldspec_agent_session.py start --source /path/to/HLD.md --target /path/to/target
python3 scripts/hldspec_agent_session.py status --target /path/to/target
python3 scripts/hldspec_agent_session.py review --target /path/to/target
python3 scripts/hldspec_agent_session.py continue --target /path/to/target
python3 scripts/hldspec_agent_session.py doctor --target /path/to/target
```

Agents should prefer the facade over low-level scripts unless debugging a failure.

## Development and handoff discipline

Local repo state is authoritative. GitHub is only the sync target. Do not push unless explicitly instructed.

Before patching:

```text
git status --short
inspect dirty files
inspect related code
inspect related tests
define behavior changed
define files expected to change
```

After patching:

```text
py_compile changed Python
focused tests
related regression tests
full tests_v2
generated-output smoke, if generated files changed
git diff --check
git status --short
```

Use `docs/HLDSPEC_GAP_HANDOFF_TEMPLATE.md` when handing work to another agent or session.

## Documentation map

| File | Purpose |
|---|---|
| `AGENTS.md` | Agent bootstrap and hard rules |
| `docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md` | Canonical architecture and terminology |
| `docs/SPECKIT_PROXY_PROTOCOL.md` | HLDspec to SpecKit handoff protocol |
| `docs/SPECKIT_SLICE_CONTROL.md` | Technical slice-controlled implementation model |
| `docs/HLDSPEC_GAP_HANDOFF_TEMPLATE.md` | Standard handoff template for current gaps/status |
| `docs/DOCS_INDEX.md` | Full doc index and active/archive map |
| `docs/HLDSPEC_DEVELOPMENT_HANDOFF.md` | Durable repo-development handoff protocol |
| `docs/HLDSPEC_DEVELOPMENT_BACKLOG.md` | Durable backlog of unfinished work |
| `docs/TEST_STRATEGY_V2.md` | Test strategy and conventions |
