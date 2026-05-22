# HLDspec V2 TODO

made by AI

## Goal

Replace fast patchwork with a proper state-machine architecture that enables reliable progress.

HLDspec should become a workflow engine for turning a raw HLD into safe SpecKit-ready artifacts.

The system must support:

```text
- raw HLD conversion
- product / architecture / governance marking
- conversion decision checkpoints
- source-HLD safety
- spec-build planning
- plan quality gates
- SpecKit prework
- approval gates
- RunSkeptic reviews
- future bounded agent orchestration
```

## Current rewrite decision

Legacy tests are preserved but moved aside during V2 rewrite.

```text
tests_legacy/ = old tests, kept for reference
tests_v2/     = active V2 contract and machine tests
```

Do not delete legacy tests blindly.

Allowed deletion policy:

```text
legacy brittle test removed
stronger V2 contract/behavior test added
same commit
V2 gate passes
```

## Architecture target

```text
hldspec/
  state_machine.py
  result_renderer.py
  artifacts.py
  command_runner.py
  checkpoints.py
  machines/
    project.py
    raw_hld_conversion.py
    apply_hld_conversion.py
    spec_build_plan.py
    speckit_prework.py
    approval_gate.py
    source_update.py
    ready_gate.py
    runskeptic_review.py
    constitution_quality.py
```

Scripts become adapters:

```text
scripts/hldspec_v2.py
scripts/hldspec_v2_ready_gate.py
scripts/project_continue.sh
scripts/hldspec_run.sh
```

Shell scripts should become compatibility wrappers only.

## Shared contracts

### MachineResult

Every machine returns:

```text
machine
state
status
checkpoint
actions_run
artifacts_written
errors
```

Statuses:

```text
CONTINUE
STOP_CHECKPOINT
BLOCKED
DONE
ERROR
```

Exit codes:

```text
0 = OK / done / continue
1 = tool error
2 = human checkpoint required
3 = gate blocked
4 = unsafe action attempted
```

### Checkpoint

Every checkpoint contains:

```text
kind
blocking_reason
human_questions
controlling_artifacts
next_action
forbidden_actions
```

Every rendered checkpoint must show:

```text
Current checkpoint:
Blocking reason:
Human decision needed:
Controlling artifacts:
Continuation protocol:
What is not modified / not invoked:
```

## Machines and responsibilities

### ProjectMachine

Status: started

Owns:

```text
- top-level coordination
- selecting the next sub-machine
- preserving sub-machine MachineResult semantics
```

Does not own:

```text
- detailed checkpoint policy
- SpecKit invocation details
- source-HLD mutation logic
```

### RawHldConversionMachine

Status: started

Owns:

```text
- raw/converted working HLD detection
- conversion decision queue inspection
- open human questions
- STOP_CHECKPOINT when decisions are TBD
- CONTINUE when all decisions are answered
```

Must never:

```text
- modify the source HLD
- invoke SpecKit
- implement app code
```

### ApplyHldConversionMachine

Status: next

Owns:

```text
- apply answered conversion decisions
- modify only the working HLD under workspace
- write conversion/apply artifacts
- preserve source HLD unchanged
```

Tests needed:

```text
answered queue + raw working HLD -> converted working HLD
source HLD remains unchanged
missing queue -> BLOCKED
TBD queue -> STOP_CHECKPOINT, not apply
invalid decision -> BLOCKED
```

### SpecBuildPlanMachine

Status: planned

Owns:

```text
- inspect spec_build_plan.json
- inspect spec_build_plan_review.md
- determine plan gate green / blocked
- identify conflicts and flagged specs
```

Outputs:

```text
CONTINUE when plan is green
BLOCKED when plan quality fails
STOP_CHECKPOINT when human decision is needed
```

### SpeckitPreworkMachine

Status: planned

Owns:

```text
- constitution update plan
- feature dependency graph
- SpecKit input manifest
- SpecKit invocation queue
- proxy dossier
- prework package
- prework quality review
```

Outputs:

```text
SPECKIT_PREWORK_MISSING
SPECKIT_PREWORK_REWORK
SPECKIT_PREWORK_APPROVAL_GATE
```

### ApprovalGateMachine

Status: planned

Owns:

```text
- approve / reject / request changes
- post-approval allowed next action
- explicit block on SpecKit until approval
```

### SourceUpdateMachine

Status: planned

Owns:

```text
- source-HLD-affecting update queue
- decision appendix
- explicit source-edit approval
```

Important:

```text
source HLD mutation is a separate risk class
source HLD must never be changed implicitly
```

### ReadyGateMachine

Status: planned

Owns:

```text
- V2 required files
- tests_v2
- generated output ignored
- optional target-HLD dry run
```

### RunSkepticReviewMachine

Status: planned

Owns:

```text
- strict RunSkeptic execution contract
- evidence fields
- PASS / ACTION / CONFLICT result shape
```

### ConstitutionQualityMachine

Status: planned

Owns:

```text
- constitution rule completeness
- HLD evidence
- violation examples
- SpecKit phase enforcement
- unresolved open questions
```

## Current active next leaps

### Leap 1: ApplyHldConversionMachine

Implement the first true action machine.

Scope:

```text
hldspec/machines/apply_hld_conversion.py
tests_v2/test_apply_hld_conversion_machine.py
docs/HLDSPEC_APPLY_HLD_CONVERSION_MACHINE.md
```

Expected behavior:

```text
RawHldConversionMachine returns CONTINUE
ProjectMachine delegates to ApplyHldConversionMachine
ApplyHldConversionMachine applies decisions to working HLD only
ProjectMachine returns CONTINUE / WORKING_HLD_CONVERTED
```

Non-goals:

```text
- no SpecKit
- no source HLD edits
- no app code
```

### Leap 2: SpecBuildPlanMachine

After conversion is applied, inspect the first-readonly plan artifacts.

Scope:

```text
hldspec/machines/spec_build_plan.py
tests_v2/test_spec_build_plan_machine.py
docs/HLDSPEC_SPEC_BUILD_PLAN_MACHINE.md
```

Expected behavior:

```text
missing review -> BLOCKED or need first-readonly
bad plan -> BLOCKED / SPEC_BUILD_PLAN_CHECKPOINT
green plan -> CONTINUE
```

### Leap 3: SpeckitPreworkMachine

Move prework readiness into a dedicated machine.

Scope:

```text
hldspec/machines/speckit_prework.py
tests_v2/test_speckit_prework_machine.py
docs/HLDSPEC_SPECKIT_PREWORK_MACHINE.md
```

### Leap 4: V2 runner migration

Only after the machines are tested:

```text
scripts/project_continue.sh -> wrapper only
scripts/hldspec_run.sh -> wrapper only
scripts/hldspec_v2.py -> active project runner
```

## Test strategy

Run only active V2 tests during the rewrite:

```bash
uv run python -m unittest discover -s tests_v2 -v
```

Run V2 ready gate:

```bash
uv run python scripts/hldspec_v2_ready_gate.py \
  --repo . \
  --output-dir .hldspec-v2-ready-gate \
  --fail-on-not-ready
```

Legacy tests are reference material only during the V2 rewrite.

## Quality rules

Every patch must:

```text
- touch one architecture seam or one full vertical slice
- run tests_v2
- run hldspec_v2_ready_gate.py
- commit only intended files
- preserve source-HLD safety
- not invoke SpecKit unless explicitly approved
```

## Stop conditions

Stop and ask for human decision when:

```text
- conversion decision is TBD
- source-HLD update is proposed
- plan quality has conflict
- SpecKit prework requires rework
- SpecKit invocation is requested
- implementation/code generation would start
```

## Current known risks

```text
- old tests may encode useful behavior but brittle implementation checks
- V2 may drift unless legacy behaviors are reviewed before deletion
- applying conversion must be very careful not to touch source HLD
- SpecKit approval must remain explicit
- generated artifacts must not pollute git status
```

## Next command after this TODO is committed

Start Leap 1:

```text
Add ApplyHldConversionMachine
```

Implement only the working-HLD conversion action.

## Operating model: roles, subagents, and context

### Core idea

HLDspec V2 is not only a script rewrite.

It is a controlled agent/workflow system for using the right context, right role, right cost, and right checkpoint for each task.

The system must help a limited agent work correctly without loading the whole repo or the whole HLD every time.

### Primary roles

```text
Judge / orchestrator
  owns the top-level state machine, checkpoint decisions, human questions, and safety boundaries

Product reviewer
  checks user value, feature boundaries, personas, use cases, acceptance criteria, and whether something is actually a spec

Architecture reviewer
  checks responsibilities, boundaries, coupling, decoupling, dependencies, source of truth, and whether architecture constraints are preserved

Governance reviewer
  checks constitution impact, assumptions, conflicts, policy decisions, source-HLD safety, and approval gates

Interface contract reviewer
  checks APIs, CLI, events, request/response contracts, consumer dependencies, compatibility, and error contracts

Data/state reviewer
  checks data ownership, persistence, mutation rules, source of truth, and dependent consumers

Processing behavior reviewer
  checks workflows, runtime behavior, validation, algorithms, failure modes, and observable outcomes

Security reviewer
  checks auth, permissions, secrets, token handling, exposure risks, and safety constraints

Operations reviewer
  checks deployment, rollback, observability, runbooks, environment assumptions, and recovery concerns

RunSkeptic reviewer
  applies the actual RunSkeptic framework strictly and returns PASS / ACTION / CONFLICT with evidence fields

Uncle Bob / SOLID reviewer
  checks SRP, OCP, DIP, ISP, testability, seams, interfaces, contracts, and refactor quality
```

### Subagent rules

Subagents are not free-form chat helpers.

They are bounded review units with explicit input, output, cost, and stop rules.

Each subagent must receive only:

```text
- the current candidate section or artifact
- the role-specific questions
- relevant prior decisions
- required output schema
- explicit forbidden actions
```

Each subagent must return:

```text
role
scope reviewed
observed evidence
evidence level
confidence
findings
unknowns
human questions
recommended state transition
residual risk
```

Subagents must not:

```text
- inspect the entire repo unless explicitly needed
- rewrite unrelated files
- invoke SpecKit
- modify source HLDs
- implement application code
- ask vague questions
- continue past a human checkpoint
```

### Bloat guard

The simpler the task, the stricter and smaller the prompt should be.

The weaker or cheaper the agent can be, the better, if it is sufficient for the task.

Rules:

```text
simple deterministic task
  -> local script or weak/cheap agent

single-file classification
  -> narrow subagent with only that section and role questions

cross-artifact consistency check
  -> bounded reviewer with explicit artifact list

architecture conflict or source-HLD mutation risk
  -> judge/orchestrator + RunSkeptic + human checkpoint

SpecKit invocation
  -> only after explicit approval gate
```

Bloat guard must support delegation:

```text
Top-level judge can delegate to a subagent.
Subagent can delegate to an even smaller reviewer if that reduces context/cost safely.
Delegation must preserve evidence, scope, and stop conditions.
```

### Context tailoring

Context must be assembled by task type.

Do not load everything by default.

Context packs:

```text
Raw HLD marking context
  source section, parent heading, neighboring headings, candidate ID, current conversion action, role questions

Conversion decision context
  decision queue item, split proposal, source excerpt, evidence, prior answered decisions

Spec build plan context
  planned spec, dependencies, quality flags, evidence section IDs, conflicting requirements

Constitution context
  proposed rule, HLD evidence, violation example, enforced SpecKit phase, affected artifacts, open questions

Prework approval context
  prework package, quality review, proxy dossier, dependency graph, first-feature case, feedback impact rules

RunSkeptic context
  exact artifact under review, actual RunSkeptic framework, issue hypothesis, tests/evidence, residual risk
```

### Prompt and personality guidance

Prompts should be role-specific and strict.

Default style:

```text
- direct
- evidence-based
- no filler
- no broad exploration unless required
- ask only real checkpoint questions
- do not summarize the whole repo
- report current state, blocker, decision needed, artifacts, next action
```

For limited agents:

```text
- read the shortest run card first
- do not read long docs unless directed by state machine
- run the assigned command
- inspect only controlling artifacts
- stop at checkpoint
```

For judge/orchestrator:

```text
- owns global consistency
- may invoke bounded subagents
- must consolidate findings
- must keep the human in the loop at checkpoints
- must never hide blockers behind generic "continue"
```

### Checkpoint communication standard

Every checkpoint must say:

```text
Current checkpoint:
Blocking reason:
Human decision needed:
Allowed options:
Controlling artifacts:
Already answered decisions:
Continuation protocol:
What happens after the answer:
What is not modified / not invoked:
```

Answered questions must be separated from active blocking questions.

The active question list must include only open blocking questions.

### Source-HLD safety

There are three different artifacts:

```text
source HLD
  original user/project file, never modified implicitly

working HLD
  workspace copy used for HLDspec conversion and metadata

source update queue
  explicit proposed updates that may affect source HLD later
```

Rules:

```text
- source HLD mutation is a separate risk class
- source HLD updates require explicit approval
- conversion applies only to working HLD
- source-HLD-affecting updates go to SourceUpdateMachine
- no machine may silently write to the source HLD
```

### SpecKit safety

SpecKit is blocked until explicit approval.

Before SpecKit:

```text
- raw HLD conversion complete
- spec build plan green
- prework quality green
- constitution case documented
- dependency/architecture case documented
- first-feature case documented
- feedback impact rules documented
- human approval captured
```

Forbidden before approval:

```text
- do not invoke SpecKit
- do not write final specs manually
- do not implement app code
```

### RunSkeptic use

RunSkeptic must be applied as a strict recipe, not as vague skepticism.

For HLDspec work, RunSkeptic findings must include:

```text
observed_evidence
evidence_level
confidence
unknowns
verification
residual_risk
PASS / ACTION / CONFLICT
```

RunSkeptic must be used for:

```text
- architecture changes
- test deletion/replacement
- source-HLD mutation policy
- SpecKit approval
- contract changes
- large refactors
```

### Uncle Bob / SOLID use

Uncle Bob / SOLID review must be used for code architecture.

Required checks:

```text
SRP
  one reason to change per machine/module

OCP
  add behavior through new machine/renderer/checklist, not shell prose rewrite

DIP
  shell depends on stable Python CLI; machines depend on contracts, not concrete scripts

ISP
  narrow contracts: MachineResult, Checkpoint, ArtifactRef, HumanQuestion

Testability
  test transitions and contracts, not exact implementation strings
```

### Product correctness guard

HLDspec must not produce fake specs.

A section should become a spec only when it has clear product capability, interface contract, data/state responsibility, processing behavior, or implementation-relevant constraint.

Context-only sections should remain context, governance, constitution, or planning material.

Examples likely not standalone specs unless they contain real requirements:

```text
milestones
background
overview
status
notes
principles
```

Unknown section rule:

```text
unknown / neutral section
  -> primary_role = TBD
  -> evidence_level = unknown
  -> no architecture default
  -> human/judge review required
```

### Current strategic direction

The next big leaps should prioritize product correctness and workflow safety, not adapter plumbing.

Priority order:

```text
1. ApplyHldConversionMachine
2. SourceUpdateMachine
3. SpecBuildPlanMachine
4. SpeckitPreworkMachine
5. ApprovalGateMachine
6. V2 runner migration
7. Replace/delete legacy tests only when covered by stronger V2 tests
```

### What not to do

```text
- do not keep patching old shell wording
- do not build thin adapters with no product value
- do not delete all tests without replacements
- do not run old brittle tests as active V2 gates
- do not invoke SpecKit prematurely
- do not spend paid agent credits on deterministic local commands
```
