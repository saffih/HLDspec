# HLDspec Development Backlog

## Purpose

This is the durable backlog for developing HLDspec itself.

It captures unfinished work and open design decisions that must survive handoff between models, agents, and sessions.

Use together with:

- `docs/HLDSPEC_DEVELOPMENT_HANDOFF.md`
- `.hldspec-dev/handoff/HANDOFF.md`
- `TASKS.md`

## Core product direction

HLDspec is agent-first and stateless.

Rules:

1. HLDspec core keeps no hidden internal memory.
2. Reads and writes are external.
3. Before source and target are known, the agent interviews the user to understand intent.
4. Once source and target are known, durable run state is written externally under the target workspace.
5. HLDspec development handoff state is written externally under `.hldspec-dev/`.
6. Scripts are deterministic tools for agents.
7. Product usage is agent-first.
8. Direct script use is allowed for maintainer/debug usage only.

## Current readiness mark - 2026-05-26

This is a working mark for the current `main` branch after the agent-first facade, development handoff/backlog, and TargetWorkspaceAdapter changes.

Update from the path-contract patch:

- canonical agent-first HLDspec-owned sync path is `target/.hldspec/sync/`
- canonical agent-first event log path is `target/.hldspec/events.jsonl`
- `target/.specify/` remains SpecKit-owned
- legacy scripts may write scratch output under `target/.hldspec/tool-runs/`, then ProjectMachine mirrors promoted artifacts through `TargetWorkspaceAdapter`

Scale:

```text
0 = absent
5 = partially designed and partially implemented
10 = product-ready with enforcement and tests
```

| Area | Mark | Current assessment |
|---|---:|---|
| Development handoff discipline | 7 | Canonical docs and generator exist; open-action/conflict quality still needs tightening. |
| Agent-first product model | 5 | Docs and facade exist; orchestration is still mostly printed guidance. |
| Target workspace clarity | 5 | Canonical new-layout paths are defined and partly tested; broader journey coverage remains. |
| TargetWorkspaceAdapter | 5 | Adapter exists with legacy/new modes; agent-first continue now selects new layout. |
| Use-case/API definition | 5 | Full UC catalog is now documented; implementation coverage and validators remain. |
| Stateless external IO | 4 | Direction is documented; enforcement tests are incomplete. |
| RunSkeptic enforcement | 3 | Required in docs/prompts; not yet enforced by machines or validators. |
| Context economy | 2 | Principles are documented; context packs and validators are not implemented. |
| SpecKit delegation templates | 2 | Desired structure is documented; generated templates are not complete/enforced. |
| Validators and regression gates | 3 | Some tests exist; path-contract, command-surface, use-case, and promotion tests are missing. |

Overall current mark: 5/10.

Reason: the path contract is mostly stabilized, but use-case implementation, command-matrix enforcement, validators, RunSkeptic gates, context economy, and promotion gates remain open.

## P0 backlog

### P0-001 Stateless external IO contract

Define and enforce:

```text
HLDspec core is stateless.
All durable run state is external.
Target-product state lives in target/.
HLDspec-development handoff state lives in .hldspec-dev/.
```

Required:

- source/target discovery behavior
- no hidden global state
- no internal untracked memory
- tests proving state files are created only under approved external locations

### P0-002 User interview capability

Add an interview flow for the user working in the HLDspec repo.

Purpose:

- understand user intent before writing
- identify source HLD/resources
- identify target directory
- classify intent: create, update, upgrade, adopt, resume, review, debug
- collect constraints, special requirements, and approval expectations

Rules:

- before source and target are known, interview answers remain session context
- after source and target are known, answers are written as external evidence
- answers feed HLD generation, constitution extraction, package slicing, prompts, and RunSkeptic gates

Suggested artifacts after target is known:

```text
target/.hldspec/interview_answers.json
target/.hldspec/interview_answers.md
```

### P0-003 TargetWorkspaceAdapter

Add an adapter so machines stop hardcoding legacy paths.

Current mismatch:

```text
new model: target/targetHLD/HLD.md
old machines: workspace/HLD.md and workspace/firstrun/
```

Required adapter fields:

```text
target_root
working_hld
raw_hld
hldspec_dir
specify_dir
sync_dir
events_path
firstrun_dir
```

Safe approach:

1. add adapter
2. update ProjectMachine first
3. migrate machines one by one
4. preserve legacy compatibility during transition

### P0-004 Event and state ownership

Move HLDspec event/log ownership out of SpecKit-owned paths.

Preferred new path:

```text
target/.hldspec/events.jsonl
```

SpecKit-owned paths remain under:

```text
target/.specify/
```

Compatibility may read old paths, but new HLDspec writes should use HLDspec-owned paths.

### P0-005 Agent-first CLI facade integration

Desired public commands:

```text
hldspec start
hldspec status
hldspec review
hldspec continue
hldspec diff
hldspec doctor
```

Next fix:

- `continue` should call ProjectMachine through TargetWorkspaceAdapter
- it should not only print the likely next tool
- direct scripts remain maintainer/debug tools

### P0-006 Context economy enforcement

Implementation still needed:

```text
target/.hldspec/context_packs/
target/.hldspec/allowed_evidence.json
target/.hldspec/forbidden_reads.md
model_tier per task
prompt context validator
```

Every delegated task must declare:

- allowed evidence
- forbidden broad reads
- model tier
- max scope
- stop condition
- RunSkeptic triggers

### P0-007 SpecKit delegation templates

Add generated prompt templates:

```text
target/prompts/speckit/<package-id>/
  01-specify.md
  02-clarify.md
  03-plan.md
  04-research-data-contracts.md
  05-tasks.md
  06-implement.md
  07-verify-runskeptic.md
```

Each prompt must include:

- target directory
- package id/name
- exact SpecKit phase
- allowed evidence files
- forbidden broad reads
- preloaded HLD knowledge
- relevant constitution rules only
- relevant backend technology choices only
- RunSkeptic trigger points
- unit/integration/e2e expectations
- stop condition
- expected outputs
- human checkpoint rules

### P0-008 Validators

Add validators for:

- backend upgrade has trigger
- selected principle has evidence
- constitution contains no feature-specific content
- each package has unit/integration/e2e testability
- prompt includes RunSkeptic rules
- prompt includes cost/context rules
- dependency graph and invocation queue match
- generated handoff points to canonical backlog and handoff protocol

### P0-009 README and AGENTS alignment

Rules:

- `AGENTS.md` first screen points to `docs/HLDSPEC_DEVELOPMENT_HANDOFF.md`
- `AGENTS.md` first screen points to `docs/HLDSPEC_DEVELOPMENT_BACKLOG.md`
- `CLAUDE.md` points to the same protocol/backlog
- generated `HANDOFF.md` points to the protocol and backlog
- low-level scripts are documented as tools, not product workflow

### P0-010 RunSkeptic enforcement

Implementation still needed:

- gate machines surface RunSkeptic status
- prompt templates include RunSkeptic trigger points
- validators block missing evidence
- generated handoff packet lists RunSkeptic PASS/ACTION/CONFLICT status

### P0-011 Canonical target path contract

Define one canonical path contract before further migration.

Current contract:

```text
Canonical agent-first layout: target/.hldspec/sync/ and target/.hldspec/events.jsonl.
Legacy/debug layout: workspace/firstrun/.specify/sync/ and workspace/.specify/sync/hldspec_event_log.jsonl.
SpecKit-owned layout: target/.specify/ and target/specs/.
```

Acceptance:

- `docs/HLD_TO_TARGET_WORKSPACE.md`, `TargetWorkspaceAdapter`, `scripts/hldspec_agent_session.py`, and `ProjectMachine` describe and use the same paths.
- tests fail if a new path model is introduced without updating the adapter and docs.

### P0-012 ProjectMachine new-layout integration

Make the agent-first target workflow call ProjectMachine through the new layout.

Acceptance:

- a test proves `ProjectMachine` receives or uses `target/targetHLD/HLD.md` for agent-first target runs.
- a test proves new event writes use `target/.hldspec/events.jsonl`.
- legacy tests still pass.

### P0-013 Agent prompt and tool-manifest path alignment

Generated agent prompts must use the adapter path contract.

Acceptance:

- generated prompts derive paths from `TargetWorkspaceAdapter`.
- generated prompts include allowed evidence and forbidden broad reads.
- generated prompts state which paths are HLDspec-owned and which are SpecKit-owned.

### P0-014 Complete use-case catalog and command/API contract

All HLDspec use cases must be defined before deeper orchestration work continues.

Required use-case catalog:

```text
UC-001 start with no source yet: interview for intent and source/target
UC-002 start with source only: choose/create target
UC-003 create new target from raw HLD
UC-004 adopt existing target without HLDspec state
UC-005 resume existing HLDspec target
UC-006 update after source/resources changed
UC-007 upgrade after HLDspec guidance/templates changed
UC-008 review checkpoint and capture human decisions
UC-009 continue after approval
UC-010 handle unresolved conflict and require human decision
UC-011 generate use-case/API map
UC-012 generate package/dependency/invocation queue
UC-013 generate context packs and bounded prompts
UC-014 delegate one SpecKit phase
UC-015 answer SpecKit clarification from evidence only
UC-016 escalate unknown SpecKit question to human
UC-017 verify SpecKit output and RunSkeptic findings
UC-018 detect stale artifacts and rebuild affected outputs
UC-019 brownfield target with existing specs
UC-020 user-requested pause before continuing
UC-021 development handoff between agents/models
UC-022 maintainer/debug direct-script run
UC-023 completed history / merged-work audit
```

Acceptance:

- each use case has trigger, preconditions, command/API, artifacts read, artifacts written, stop condition, and tests expected.
- command names match the facade or are clearly marked legacy/future.
- no product use case requires direct user knowledge of low-level scripts.

### P0-015 Product command surface parity

Make docs, CLI parser, tests, and prompts agree on supported commands.

Current conflict:

- product docs mention `hldspec speckit` and `hldspec stop` or equivalent future controls.
- current parser does not implement them.
- older use-case docs mention `run`, `interview`, `prework`, and `speckit-proxy`.

Acceptance:

- one command matrix lists supported, future, and legacy/debug commands.
- CLI parser tests cover every supported command.
- docs do not advertise unsupported commands as current product behavior.

### P0-016 Path-contract and command-contract regression tests

Add tests that lock the product contract.

Required tests:

- target workspace path contract.
- ProjectMachine new-layout entry path.
- event log new-layout path.
- first-run/sync path consistency.
- prompt/tool-manifest path consistency.
- README/AGENTS/USER_RUN_MODEL command consistency.
- unsupported command docs are marked future or legacy.

### P0-017 Promotion scorecard gate

Do not promote HLDspec as product-stable without an explicit scorecard gate.

Acceptance:

- scorecard lists current mark, target mark, blockers, and next safe step.
- any mark above 7 requires tests or reproduced evidence.
- unresolved ACTION/CONFLICT items block promotion.

## P1 backlog

### P1-001 Backend toolbox cleanup

Refine `docs/BACKEND_TECHNOLOGY_RECOMMENDATION.md`.

Known issue:

```text
Domain structure | Clean architecture | Ports/adapters
```

This mixes architecture style and implementation boundary pattern.

Better split:

```text
Domain structure:
Default = modular clean layers
Upgrade = explicit boundary layer

Boundary isolation:
Default = direct internal interface
Upgrade = port/adapter
Trigger = external dependency, replaceability, test seam, agent/tool boundary
```

### P1-002 Development handoff generator maturity

Generated `.hldspec-dev/handoff/HANDOFF.md` should include:

- pointer to canonical handoff protocol
- pointer to backlog
- git state
- changed files
- tests run
- tests required
- RunSkeptic status
- open actions
- open conflicts
- next safe step
- do-not-do list

### P1-003 HLD build terminology

Choose one product term and use it consistently.

Candidate:

```text
hldspec start
```

Meaning:

```text
start an agent-guided HLDspec session
```

Optional future command:

```text
hldspec build-hld
```

Meaning:

```text
build or improve target/targetHLD/HLD.md from sources and interview answers
```

Avoid using `build` ambiguously for both HLD preparation and product implementation.

### P1-004 Diff and stale detection

Track fingerprints:

```text
target/.hldspec/input_manifest.json
target/.hldspec/artifact_hashes.json
```

Detect:

- source changed
- guidance changed
- generated prompts stale
- SpecKit outputs changed
- dependency graph changed
- invocation queue stale

### P1-005 HLDspec development scorecard

Keep a scorecard updated for:

- user simplicity
- agent-first workflow
- statelessness
- target workspace clarity
- RunSkeptic enforcement
- context economy
- SpecKit handoff
- testability
- validators
- development handoff quality

## P2 backlog

### P2-001 Optional workflow engine evaluation

Do not add a workflow engine now.

Trigger only if:

- persistent loop becomes too complex
- timers/retries/workers exceed simple state machine needs
- current adapter/machine model cannot safely express workflow

### P2-002 Microservices and event sourcing are not defaults

Keep these as rare optional tools.

Use only with RunSkeptic-approved triggers.

### P2-003 UI/accessibility templates

If HLDspec later generates UI-related package prompts, include accessibility checks:

- keyboard navigation
- screen reader labels
- contrast
- focus order
- semantic structure
- clear errors

## Open conflicts

### CONFLICT-001 Product workflow vs maintainer workflow

Decision:

```text
Product usage is agent-first.
Maintainer/debug usage may run scripts directly.
```

Required implementation:

- README leads with agent-first usage
- direct scripts are documented as tools/debug
- agents know scripts are not the public product workflow

### CONFLICT-002 Target layout migration strategy

Decision:

```text
Use TargetWorkspaceAdapter and migrate machines incrementally.
```

Implementation rule:

```text
Agent-first ProjectMachine calls use `layout="new"`.
Legacy/debug runs may keep `layout="legacy"` until migrated.
```

### CONFLICT-003 First-run and sync path ownership

Resolved decision:

```text
Should first-run review/sync artifacts live under target/.hldspec/, target/.specify/, or target/firstrun/.specify/sync/?
```

Decision:

- HLDspec-owned review and planning artifacts live under `target/.hldspec/sync/` for the agent-first layout.
- Event history lives under `target/.hldspec/events.jsonl`.
- SpecKit-owned final artifacts remain under `target/.specify/` and `target/specs/`.
- Legacy/debug runs may still read or write old `.specify/sync` shapes through the adapter during migration.

### CONFLICT-004 Use-case API doc vs current facade

Decision: keep the current public surface small; mark richer commands as future and old names as legacy/debug.

Current public commands: `start`, `status`, `review`, `continue`, `diff`, `doctor`.

Future commands: `interview`, `prework`, `speckit`, `pause`.

Legacy/debug: `run`, `speckit-proxy`, direct low-level scripts.

Decision record:

```text
Should the canonical public command set be start/status/review/continue/diff/doctor only, or should run/interview/prework/speckit-proxy/speckit/pause also be product commands?
```

Safe recommendation:

- keep the current public surface small.
- mark unimplemented commands as future or legacy/debug.
- define all use cases independently of command spelling.
- map each use case to current/future/legacy command status.

## Next safe patch sequence

1. Stabilize the canonical target path contract.
2. Update TargetWorkspaceAdapter, ProjectMachine entry, agent prompt generation, and docs to match that contract.
3. Add path-contract regression tests.
4. Complete the use-case catalog and command/API matrix.
5. Align README, AGENTS, USER_RUN_MODEL, and HLDSPEC_USE_CASES_AND_API.
6. Make `continue` call ProjectMachine through the adapter instead of only printing guidance.
7. Move event log writes to `target/.hldspec/events.jsonl` for the new layout.
8. Add interview artifacts.
9. Add context-pack and prompt validators.
10. Add RunSkeptic promotion gates.
