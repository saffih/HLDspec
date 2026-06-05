# Anti-Drift Contracts

## Purpose

Anti-drift contracts protect HLDspec's product identity, ownership boundaries, implementation guidance model, and engineering doctrine.

They are not feature specs and they are not prose snapshots. A future patch may improve wording or implementation, but it must not weaken, remove, rename, or scatter these protected concepts without an explicit reviewed replacement.

## Core rule

Protect contracts, not paragraphs.

A change may rewrite docs or code, but it must preserve the four contracts below or replace them with an explicitly reviewed stronger equivalent.

## Contract 1: Product model contract

### What must remain true

- HLDspec is an agent-first control layer around HLD-driven SpecKit work.
- HLDspec supports three user journeys:
  1. HLD Authoring
  2. SpecKit Preparation
  3. Implementation Guidance
- SpecKit Preparation is the core product.
- HLDspec does not replace SpecKit.
- HLDspec does not implement the target product by itself.

### Canonical docs

- `README.md`
- `docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md`

### Forbidden dilution

- Do not reduce HLDspec to only a prompt/doc generator.
- Do not redefine HLDspec as a direct autonomous implementation agent.
- Do not drop any of the three user journeys.
- Do not imply Implementation Guidance means HLDspec owns implementation.

### Test expectations

Tests must fail if the three journeys disappear, if SpecKit Preparation is no longer identified as the core product, or if docs imply HLDspec replaces SpecKit.

## Contract 2: Source-truth and SpecKit ownership contract

### What must remain true

- The HLD remains the product source of truth.
- HLDspec owns `.hldspec/source_package/`.
- `.specify/source/` is a generated read-only mirror.
- The real `.specify/` workspace is SpecKit-owned.
- SpecKit owns spec, plan, tasks, and implementation artifacts.
- HLDspec must not fake a SpecKit workspace.
- Build Loop trigger phrases are protected: `SOURCE_PACKAGE_READY`,
  `INIT_PREREQS_READY`, `WORKSPACE_INITIALIZED`, `MIRROR_SYNCED`,
  `READY_FOR_SPECIFY`, and `BUILD_LOOP_ACTIVE`.
- The trigger order is source package, init prerequisites, real workspace init,
  post-init mirror sync, ready for specify, then active build loop.

### Canonical docs and code

- `docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md`
- `hldspec/hld_source_package.py`
- `hldspec/speckit_workspace.py`

### Forbidden dilution

- Do not edit `.specify/source/` as source truth.
- Do not treat `.specify/source/` as proof of real SpecKit initialization.
- Do not mirror into `.specify/source/` as the product-flow proof step before
  real SpecKit init validation.
- Do not let SpecKit or agents silently rewrite HLD truth.
- Do not mix HLDspec-owned and SpecKit-owned artifacts.

### Test expectations

Tests must fail if the source-package ownership model or read-only mirror model is removed, if a mirror-only `.specify/source/` can be treated as initialized SpecKit workspace, or if docs put mirror sync before real SpecKit init validation in the product flow.

## Contract 3: Slice, mediator, and implementation guidance contract

### Operator / Doctor / Devin Mediator Boundary

- HLDspec Operator is HLDspec core behavior.
- SpecKit Doctor is the diagnostic/preflight part of the SpecKit Operator.
- SpecKit Doctor is not the whole Operator.
- SpecKit Operator is broader than Doctor.
- HLDspec Operator includes readiness-first Operator State that gates the readiness boundary and reports post-readiness SpecKit lifecycle evidence when phase artifacts exist.
- HLDspec Operator uses target facts, source-package state, Engineering Toolbox guidance, implementation slicing, mediator/operator guidance, and SpecKit Doctor readiness facts today.
- Richer post-implementation reassessment remains planned.
- Doctor remains readiness/preflight only and must not decide the full lifecycle.
- Devin Mediator is a Devin-specific runtime adapter.
- Devin Mediator is not HLDspec core behavior.
- HLDspec does not mediate Devin directly.
- HLDspec produces operator facts, source package, Engineering Toolbox guidance, slices, and test policy.
- Devin Mediator consumes HLDspec Operator facts/artifacts to drive Devin safely.
- Devin-specific exact go/stop/session rules must not define the generic Operator layer.
- Operator / Doctor / Devin Mediator are not interchangeable names for the same thing.

### What must remain true

- HLDspec core behavior is the SpecKit Operator.
- SpecKit Doctor is the diagnostic/preflight part of the Operator.
- SpecKit Doctor is not the whole Operator.
- HLDspec uses one complete `specify -> plan -> tasks -> analyze` flow before implementation.
- Implementation then proceeds through many guided implementation slices.
- HLDspec provides and bounds slice-control.
- The user or Agent Mediator enforces slice scope during runtime.
- Devin Mediator is a Devin-specific runtime adapter.
- HLDspec does not mediate Devin directly.
- HLDspec produces operator facts, source-package state/context, Engineering Toolbox guidance, implementation slicing, mediator/operator guidance, SpecKit Doctor readiness facts, and readiness-first lifecycle Operator State today.
- Operator State must continue to surface post-readiness lifecycle states such as `PLAN_ACTIVE`, `TASKS_ACTIVE`, `ANALYZE_READY`, and `REASSESSMENT_REQUIRED` when phase artifacts exist.
- Richer post-implementation reassessment is future work, not already fully implemented.
- Devin Mediator consumes HLDspec Operator facts/artifacts.
- Agent Mediator is not the Implementation Agent.
- Implementation Agent runs SpecKit, edits code, and runs tests.
- Tmux or session state is visibility only, not approval state.
- Devin-specific exact go/stop/session rules must not define the generic Operator layer.
- Journey 3 mediator support preserves mode-specific control words: Devin uses exact `go` and exact `stop`; direct mediator mode may document `stop now` as optional behavior only; both modes preserve `clarify`, `rerun tests`, and `reassess`.
- Devin mediator activation syntax remains: `create agent on {path} as {session-name} using model {model} [permission-mode {mode}]`.
- Codex and Claude may use direct mediator mode, but must preserve the same mediator boundaries and evidence rules.

### Canonical docs and code

- `docs/SPECKIT_SLICE_CONTROL.md`
- `docs/SPECKIT_PROXY_PROTOCOL.md`
- `docs/MEDIATOR_PROMPT_PROTOCOL.md`
- `hldspec/implementation_slicing.py`

### Forbidden dilution

- Do not claim HLDspec hard-enforces runtime slices unless code actually does.
- Do not let agents run all tasks by default.
- Do not confuse Agent Mediator with Implementation Agent.
- Do not let Devin-specific exact go/stop/session rules define the generic Operator layer.
- Do not let generic Operator guidance require Devin/tmux/session behavior.
- Do not let Doctor readiness be treated as full lifecycle operation.
- Do not let the mediator approve completion alone.
- Do not treat tmux output as source truth or approval.
- Do not remove or weaken the Devin mediator activation syntax without an explicitly reviewed replacement.
- Do not let failed tests, missing evidence, or scope expansion be hidden by the mediator.

### Test expectations

Tests must fail if docs remove the one-full-flow-then-slices model, if mediator and implementation-agent roles collapse into one role, if docs claim runtime slice enforcement that HLDspec does not actually perform, if the Devin mediator activation syntax disappears, or if mode-specific control words and failed-test boundaries disappear.

## Contract 4: Engineering Toolbox contract

### What must remain true

- Engineering Toolbox is durable engineering doctrine for target software.
- The HLD defines what the product should be.
- The Engineering Toolbox guides how target software should be built safely.
- The toolbox splits into:
  1. Constitution candidates
  2. Preferred Choice Selection
- Constitution candidates are stable long-lived principles proposed for project constitution after review.
- Preferred Choice Selection is context-specific engineering guidance selected from HLD or discussion triggers for SpecKit and implementation agents.
- The selected guidance path must remain:
  - `target/.hldspec/engineering/selection.json`
  - `target/.hldspec/engineering/decisions.jsonl`
  - `target/.hldspec/source_package/engineering_guidelines.md`
  - `target/.specify/source/engineering_guidelines.md`

### Non-droppable engineering concepts

- hexagonal architecture
- ports and adapters
- business logic container
- design for testability
- business logic coverage
- contract and boundary testing
- UI tester skill
- stage-safe testing
- prod/test separation
- resettable fixtures
- source-of-truth ownership
- capability stewardship
- safe test/stage environment
- no feature work corrupts the user's active product or data
- anti-drift or contract test for key capability changes

### Canonical docs

- `docs/ENGINEERING_TOOLBOX.md`
- `docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md`

### Forbidden dilution

- Do not reduce the toolbox to vague advice.
- Do not drop stage-safe testing.
- Do not drop business logic testability.
- Do not dump every toolbox card into the constitution.
- Do not treat preferred choices as permanent law.
- Do not remove the path to `engineering_guidelines.md`.
- Do not allow SpecKit prework approval to continue when generated `engineering_guidelines.md` is missing or invalid.
- Do not add key capabilities without durable docs, tests, contracts/runbooks
  where relevant, and anti-drift coverage for protected behavior.
- Do not let implementation agents test against production or user-owned data without explicit approval.

### Test expectations

Tests must fail if the toolbox split disappears, if the selected-guidance artifact path disappears, if `SpeckitPreworkMachine` stops blocking missing or invalid generated engineering guidance, or if the protected clean-software, testability, and stage-safety concepts are removed.

## Change policy

A future patch may change any protected term only by doing all of the following:

1. Name the contract being changed.
2. Explain the replacement.
3. Prove the replacement preserves or strengthens the contract.
4. Update docs and tests in the same patch.
5. Run the focused anti-drift tests and the full `tests_v2` suite.

If a patch weakens a protected contract without this process, classify it as `ACTION` or `CONFLICT`, not `PASS`.
