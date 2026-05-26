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

Decision still needed:

```text
Migrate ProjectMachine directly to target/targetHLD,
or introduce TargetWorkspaceAdapter and migrate gradually.
```

Safe recommendation:

```text
Add TargetWorkspaceAdapter first.
Then migrate machines incrementally.
```

## Next safe patch sequence

1. Add or update canonical handoff/backlog pointers in `AGENTS.md`.
2. Add tests that enforce those pointers.
3. Add TargetWorkspaceAdapter.
4. Move event log writes to `target/.hldspec/events.jsonl`.
5. Add interview artifacts.
6. Add context-pack and prompt validators.
