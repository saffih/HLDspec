# HLD to Target Workspace

## Purpose

HLDspec creates a controlled `target/` workspace for one app or domain.

Inside `target/`, HLDspec creates a `targetHLD/` directory that owns the raw HLD evidence, working HLD, HLD inventory, section slices, grouping, and HLD-to-package mapping.

HLDspec prepares. SpecKit executes. Human approval gates remain explicit.

## Core model

```text
source resources
  -> target/
  -> target/targetHLD/
  -> target/.hldspec/
  -> target/.specify/
  -> target/prompts/
  -> target/specs/
```

## Target workspace layout

```text
target/
  targetHLD/
    raw/
      HLD.raw.md
      resources_manifest.json
    HLD.md
    sections/
      HLD-001.md
      HLD-002.md
    inventory.json
    inventory.md
    groups.json
    groups.md
    spec_package_map.json
    spec_package_map.md

  .hldspec/
    state.json
    state.md
    constitution_signals.json
    constitution_update_plan.json
    constitution_update_plan.md
    spec_packages.json
    spec_packages.md
    feature_dependency_graph.json
    feature_dependency_graph.md
    speckit_invocation_queue.json
    speckit_invocation_queue.md
    quality_gates.json
    runskeptic_reviews/

  .specify/
    memory/
      constitution.md
    sync/
      speckit_proxy_dossier.json
      speckit_proxy_dossier.md

  prompts/
    mediator/
    speckit/
      001-feature-name/
        01-specify.md
        02-clarify.md
        03-plan.md
        04-checklist.md
        05-tasks.md
        06-analyze.md
        07-implement.md

  specs/
    # SpecKit-created final feature directories and files only.
```

## Directory meanings

### `target/`

The generated target workspace for one app or domain.

It contains HLDspec planning artifacts, SpecKit workspace files, generated prompts, and SpecKit-owned specs.

### `target/targetHLD/`

The HLD workspace inside `target/`.

It contains:

- raw copied HLD evidence
- resource manifest
- working canonical HLD
- extracted HLD sections
- HLD inventory
- HLD groups
- HLD-to-spec-package mapping

### `target/.hldspec/`

HLDspec-owned control and planning artifacts.

### `target/.specify/`

SpecKit-owned workspace files.

### `target/prompts/`

Generated delegation prompts for SpecKit, RunSkeptic, mediator agents, and target agents such as Devin, Claude, or Codex.

### `target/specs/`

SpecKit-created final feature specs and implementation planning outputs.

HLDspec must not manually write final SpecKit specs here.

## Source preservation

HLDspec must preserve source material.

Required behavior:

- Copy or snapshot original input into `target/targetHLD/raw/`.
- Create `target/targetHLD/HLD.md` as the working HLD.
- Treat source resources and files under `target/targetHLD/raw/` as read-only evidence.
- Make generated planning artifacts rebuildable from `target/targetHLD/HLD.md` and `target/targetHLD/raw/resources_manifest.json`.

## HLD grouping

HLDspec must group HLD sections into named work areas.

Grouping must be based on:

- logical coherence
- source-of-truth boundaries
- architecture boundaries
- API/interface ownership
- data/state ownership
- dependency order
- testability boundaries
- operational and deployment concerns

Grouping must not be arbitrary line-count splitting.

## Spec package generation

HLDspec must convert HLD groups into bite-size SpecKit-ready spec packages.

Each package must include:

- package id
- package name
- source HLD sections
- purpose
- responsibilities
- dependency relationships
- upstream and downstream consumers
- API/interface contracts
- data/state ownership
- acceptance criteria
- unit test expectations
- integration test expectations
- end-to-end testability path
- required test tools
- RunSkeptic trigger conditions
- evidence sources
- open questions
- stop condition

## Build order

HLDspec must generate:

- `target/.hldspec/feature_dependency_graph.json`
- `target/.hldspec/feature_dependency_graph.md`
- `target/.hldspec/speckit_invocation_queue.json`
- `target/.hldspec/speckit_invocation_queue.md`

The invocation queue must be derived from the dependency graph.

The queue must support building one package after another without hiding unresolved dependencies.

## Ownership boundary

HLDspec owns:

- `target/` workspace setup
- `target/targetHLD/` generation and formatting
- HLD inventory
- HLD grouping
- constitution update plan
- spec package plan
- dependency graph
- invocation queue
- delegation prompts
- RunSkeptic review assets
- quality gate definitions

SpecKit owns:

- final `spec.md`
- clarify
- `plan.md`
- `research.md`
- `data-model.md`
- `contracts/`
- `quickstart.md`
- `tasks.md`
- implementation flow

Human owns:

- constitution approval
- architecture decisions not proven by evidence
- source-of-truth decisions not proven by evidence
- feature split or merge decisions when ambiguous
- implementation approval

## Acceptance criteria

- `target/` can be resumed after interruption.
- `target/targetHLD/` cleanly separates raw HLD evidence from the working HLD.
- HLDspec artifacts are separate from SpecKit-owned outputs.
- The source HLD is not modified implicitly.
- Every package has clear evidence, tests, and stop conditions.
- The constitution remains principle-level and is not polluted by feature details.

## Software design principle integration

HLDspec must use `docs/SOFTWARE_DESIGN_PRINCIPLES.md` when creating `target/`.

The target workspace must preserve the design decisions needed to support:

- explicit interfaces and contracts
- clean architecture
- ports/adapters
- message-bus or event-driven style when justified
- state machines
- persistent loops and resumability
- accessibility for user-facing UI
- unit, integration, and end-to-end testability
- quality gates
- RunSkeptic at key junctions
- cost/context economy

These principles are not copied wholesale into every artifact. HLDspec must extract only the relevant principles into target-specific constitution rules, spec packages, and prompts.

## Runtime document usage

HLDspec must use `docs/HLDSPEC_RUNTIME_DOCUMENT_USAGE.md` during target workspace preparation.

A correct run must convert reusable guidance into target-specific artifacts, including:

- selected design principles
- backend technology recommendation
- constitution signals
- spec packages
- dependency graph
- prompts
- RunSkeptic gates

Reusable docs are guidance. Target artifacts are the controlling outputs for the specific run.
