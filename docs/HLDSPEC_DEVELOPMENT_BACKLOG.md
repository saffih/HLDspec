# HLDspec Development Backlog

## Purpose

This is the durable backlog for developing HLDspec itself.

It captures unfinished work and open design decisions that must survive handoff between models, agents, and sessions.

Use together with:

- `docs/HLDSPEC_DEVELOPMENT_HANDOFF.md`
- `.hldspec-dev/handoff/HANDOFF.md`
- `TASKS.md`
- `docs/HLDSPEC_PRODUCT_SCORECARD.md`
- `docs/HLDSPEC_PRINCIPLE_ENFORCEMENT_MATRIX.md`

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

This mark reflects the current `main` branch after the command-surface, path-contract, interview-artifact, context-economy, validator, promotion-gate, UX-output, self-dogfood, and promoted-capability RunSkeptic evidence patches.

Scale:

```text
0 = absent
5 = partially designed and partially implemented
10 = product-ready with enforcement and tests
```

| Area | Mark | Current assessment |
|---|---:|---|
| Development handoff discipline | 7 | Canonical handoff/backlog docs and generator exist; generated handoff still needs stronger open-action, conflict, and RunSkeptic status quality. |
| Agent-first product model | 6 | Public facade is narrowed to `start`, `status`, `review`, `continue`, `diff`, and `doctor`; richer commands are marked future or legacy/debug; full end-to-end orchestration coverage remains open. |
| Target workspace clarity | 7 | New-layout paths are stabilized: `target/.hldspec/sync/`, `target/.hldspec/events.jsonl`, `target/targetHLD/HLD.md`, `target/targetHLD/raw/HLD.raw.md`, and SpecKit-owned `target/.specify/`; broader migration coverage remains. |
| TargetWorkspaceAdapter | 7 | Adapter supports legacy/new modes and `hldspec continue` uses ProjectMachine with new-layout metadata; remaining machines still need migration coverage. |
| Use-case/API definition | 6 | Use-case catalog and command matrix exist; implementation and journey tests do not yet cover every use case. |
| Stateless external IO | 5 | `start` and self-dogfood smoke prove target-only durable writes for key flows; enforcement across every write path remains incomplete. |
| Context economy | 6 | Context packs, allowed evidence, forbidden reads, bounded SpecKit prompts, and context validators exist; guarded product-flow integration remains. |
| SpecKit delegation prompts | 6 | Seven bounded SpecKit phase prompts are generated per package; package discovery/invocation wiring and deeper semantic validators remain. |
| Validators and regression gates | 6 | Context prompt validator, promotion gate, command/path tests, self-dogfood smoke, and matrix tests exist; domain validators remain open. |
| RunSkeptic enforcement | 6 | Prompt validators and promotion gate enforce RunSkeptic trigger/status requirements, including promoted capability RunSkeptic PASS evidence; gate-machine and handoff propagation remain open. |
| Promotion gate | 6 | Promotion gate blocks validator ACTION/CONFLICT, missing context validation, unresolved checkpoints, readiness marks above evidence, and promoted capabilities without RunSkeptic PASS evidence; not yet wired into a complete product promotion command. |
| UX/output quality | 6 | `status`, `review`, and `doctor` show decision-oriented output with blockers, validation status, promotion status, next safe action, and final summary; `start`, `diff`, and stage-aware checks need more coverage. |
| Self-dogfood | 6 | HLDspec can run a smoke flow on HLDspec backlog evidence without invoking SpecKit; full self-hosted SpecKit delegation remains out of scope and unproven. |

Overall current mark: 6/10.

Reason: the foundational contracts and several enforcement gates now exist, but HLDspec is not yet product-ready. Remaining blockers are guarded product-flow integration, end-to-end journey coverage, stale-artifact/diff handling, domain validators, and RunSkeptic status propagation through handoff/gate-machine outputs.

## Current implementation notes

### Context economy

Implemented:

- `hldspec/context_economy.py`
- `scripts/build_speckit_context_prompts.py`
- `target/.hldspec/context_packs/`
- `target/.hldspec/allowed_evidence.json`
- `target/.hldspec/forbidden_reads.md`
- bounded per-package prompts under `target/prompts/speckit/<package-id>/`

Current status: mostly addressed as artifact generation and validation. Residual work is product-flow wiring and semantic validation beyond required markers.

### SpecKit prompts

Implemented:

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

Current status: mostly addressed for bounded prompt generation. Residual work is package discovery, invocation queue integration, and validation of produced SpecKit outputs.

### Validators

Implemented:

- `hldspec/validators.py`
- `scripts/validate_hldspec_target.py`
- `target/.hldspec/validation/context_prompt_validation.json`
- `target/.hldspec/validation/context_prompt_validation.md`

Validated now:

- `allowed_evidence.json`
- `forbidden_reads.md`
- context pack JSON
- required prompt context markers
- RunSkeptic triggers
- valid model tiers
- forbidden broad-read phrases
- implement-phase human approval guards

Still open:

- backend upgrade trigger validation
- selected-principle evidence validation
- constitution purity validation
- package unit/integration/e2e testability validation
- dependency graph and invocation queue parity
- generated handoff pointer validation

### RunSkeptic enforcement

Implemented:

- generated SpecKit prompts include RunSkeptic trigger points
- context prompt validation blocks prompts that omit RunSkeptic triggers
- promotion gate blocks validator ACTION/CONFLICT findings
- promotion gate blocks promoted capabilities unless RunSkeptic status is PASS with evidence

Still open:

- gate-machine outputs must surface RunSkeptic PASS/ACTION/CONFLICT directly
- generated handoff packets must include RunSkeptic status
- missing evidence must be enforced beyond prompt text and promotion-scorecard cases

### Promotion gate

Implemented:

- `hldspec/promotion.py`
- `scripts/check_hldspec_promotion_gate.py`
- `target/.hldspec/validation/promotion_gate.json`
- `target/.hldspec/validation/promotion_gate.md`

Blocks now:

- validator ACTION/CONFLICT findings
- missing context validation when prompts exist
- unresolved human checkpoints
- missing implementation approval guards
- readiness marks above 7 without evidence
- promoted capabilities without RunSkeptic PASS evidence

Still open:

- guarded product promotion command/path
- richer scorecard fields and generated promotion summaries
- product-flow wiring so promotion checks run automatically at the right junctions

### UX output

Implemented:

- `docs/HLDSPEC_OUTPUT_CONTRACT.md`
- `docs/HLDSPEC_QUALITY_REQUIREMENTS.md`
- decision-oriented `status`, `review`, and `doctor` output

Required output sections now include:

- blockers
- validation status
- promotion status
- next safe action
- final summary

Still open:

- same output discipline for `start` and `diff`
- stage-aware `doctor` checks
- CLI journey tests for every supported command path

### Self-dogfood

Implemented:

- `docs/HLDSPEC_SELF_DOGFOOD_CONTRACT.md`
- `docs/HLDSPEC_PRINCIPLE_ENFORCEMENT_MATRIX.md`
- `tests_v2/test_self_dogfood_flow.py`

The smoke flow runs against HLDspec repository evidence, writes target session/interview/context/validation/promotion artifacts, and does not invoke SpecKit.

Still open:

- full self-hosted SpecKit handoff
- repeated stale-input and changed-guidance rebuild tests
- evidence capture for red-to-green RunSkeptic cycles

### Promoted capability RunSkeptic evidence

Implemented:

- `tests_v2/test_promoted_capability_runskeptic_gate.py`
- promotion gate requirement that every promoted capability must include RunSkeptic PASS evidence
- blocking behavior for missing, ACTION, or CONFLICT RunSkeptic status

Still open:

- generated promoted-capability scorecard creation
- human-readable promotion diff linking each promoted capability to exact evidence

## P0 backlog - still blocks product-stable claims

### P0-001 External IO enforcement across all write paths

Status: partially addressed; still P0.

Covered now:

- `start` preserves source HLD content.
- `start` writes durable target-product artifacts under `target/`.
- self-dogfood smoke verifies source evidence remains unchanged.
- target state paths are explicit and tested for key flows.

Still needed:

- tests proving every write path writes only to approved target or `.hldspec-dev/` locations
- enforcement for non-start flows, generated prework artifacts, SpecKit delegation prompts, and promotion reports
- explicit failure when a product flow attempts durable writes outside the path contract

### P0-002 Guarded product-flow integration

Status: open P0.

Problem: context economy, validators, RunSkeptic checks, and promotion gate exist as tools/gates, but the product flow still needs stronger automatic sequencing.

Acceptance:

- `hldspec continue` knows when to build context prompts, validate them, run promotion checks, and stop.
- `status`, `review`, and `doctor` agree on current blockers and next safe action.
- no product path can proceed from generated prompts to implementation while validation or promotion is ACTION/CONFLICT.

### P0-003 End-to-end journey tests

Status: open P0.

Required journeys:

- start from raw HLD source
- resume existing target
- review checkpoint and capture human decision
- continue after approval
- stop on unresolved conflict
- generate context packs and bounded prompts
- validate generated prompts
- run promotion gate
- inspect status/review/doctor output

Acceptance:

- tests use the public facade where possible
- tests prove direct low-level scripts are not required for product usage
- failures show next safe action rather than only stack traces

### P0-004 Stale artifact and diff handling

Status: open P0.

Required artifacts:

```text
target/.hldspec/input_manifest.json
target/.hldspec/artifact_hashes.json
```

Required detection:

- source changed
- guidance changed
- generated prompts stale
- SpecKit outputs changed
- dependency graph changed
- invocation queue stale

Acceptance:

- `hldspec diff` reports stale or changed artifacts clearly
- `hldspec doctor` reports whether the target is safe to continue
- regeneration scope is bounded to affected outputs

### P0-005 Domain validators before product-stable promotion

Status: open P0.

Required validators:

- backend upgrade has trigger
- selected principle has evidence
- constitution contains no feature-specific content
- each package has unit/integration/e2e testability
- dependency graph and invocation queue match
- generated handoff points to canonical backlog and handoff protocol

Acceptance:

- validators write machine-readable and human-readable reports
- ACTION/CONFLICT findings block promotion
- tests cover failing and passing cases

### P0-006 RunSkeptic status propagation

Status: open P0.

Covered now:

- prompt validators check RunSkeptic triggers
- promotion gate checks promoted capability RunSkeptic PASS evidence

Still needed:

- gate machines surface RunSkeptic PASS/ACTION/CONFLICT status directly
- generated handoff packet lists RunSkeptic status
- review output links RunSkeptic findings to exact evidence and next safe action

## Mostly addressed former P0 items

These remain important but no longer represent the top stale-truth gaps.

| Former item | Current status | Residual location |
|---|---|---|
| User interview capability | Mostly addressed for `start --source --target --comment`; future interactive discovery remains deferred. | P1-003 |
| TargetWorkspaceAdapter | Mostly addressed for new-layout ProjectMachine entry; migration coverage remains. | P1-004 |
| Event and state ownership | Mostly addressed for canonical new paths; full write-path enforcement remains. | P0-001 |
| Agent-first CLI facade integration | Mostly addressed for current public command surface and `continue`; full journey coverage remains. | P0-003 |
| Context economy enforcement | Mostly addressed as generated artifacts plus validator; product-flow integration remains. | P0-002 |
| SpecKit delegation prompts | Mostly addressed as seven generated bounded phase prompts; package/invocation wiring remains. | P1-005 |
| Context and prompt validators | Mostly addressed for prompt/context guardrails; domain validators remain. | P0-005 |
| README/AGENTS alignment | Mostly addressed for command-surface direction; final docs sweep remains. | P1-006 |
| Promotion scorecard gate | Mostly addressed as an internal target gate; product promotion command/path remains. | P0-002 |
| Self-dogfood smoke | Mostly addressed for smoke without SpecKit; full self-hosted delegation remains future. | P1-007 |

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

### P1-003 Interactive interview discovery

The current implemented path writes interview artifacts when source and target are provided.

Future work:

- no-source interview for intent and source discovery
- source-only flow for target selection
- resume/adopt interview for existing targets
- structured clarification capture before writing

### P1-004 Complete machine migration through TargetWorkspaceAdapter

Residual work:

- migrate remaining machines away from hardcoded legacy paths
- keep legacy/debug compatibility explicit
- add tests that fail if a new path model is introduced without adapter and docs updates

### P1-005 Package discovery and SpecKit invocation wiring

Residual work:

- connect bounded prompts to final package/dependency/invocation artifacts
- validate package prompts against the dependency graph
- ensure each generated prompt names allowed evidence, forbidden reads, model tier, stop condition, and expected outputs

### P1-006 Documentation alignment sweep

Residual work:

- README leads with agent-first product usage
- AGENTS, CLAUDE, USER_RUN_MODEL, and use-case docs agree on current/future/legacy commands
- direct scripts are documented as agent/maintainer tools, not the product workflow

### P1-007 Expanded self-dogfood

Residual work:

- self-run with changed HLDspec guidance
- stale-input rebuild detection
- generated promoted-capability scorecard
- RunSkeptic red-to-green evidence capture

### P1-008 HLD build terminology

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

## Next safe patch sequence

1. Review GitHub diff and RunSkeptic on this stale-truth update.
2. Wire context validation and promotion checks into guarded product-flow stops.
3. Add end-to-end journey tests through the public facade.
4. Add stale-artifact and diff detection.
5. Add domain validators for backend triggers, principle evidence, constitution purity, package testability, graph/queue parity, and handoff pointers.
6. Propagate RunSkeptic PASS/ACTION/CONFLICT through gate-machine and handoff outputs.
