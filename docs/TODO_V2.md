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

## Current implemented slice

```text
ProjectMachine
RawHldConversionMachine
ApplyHldConversionMachine
SpecBuildPlanMachine
SpeckitPreworkMachine
ApprovalGateMachine
HLDspec V2 Flow Test Runner
```

## Active test layout

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
  command_runner.py
  artifacts.py
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

Subagents are bounded review units with explicit input, output, cost, and stop rules.

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

## Source-HLD safety

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

## SpecKit safety

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

## RunSkeptic use

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

## Uncle Bob / SOLID use

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

## Product correctness guard

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

## Current active next leaps

### Leap 1: ApplyHldConversionMachine

Status: implemented in current V2 full slice.

### Leap 2: SpecBuildPlanMachine

Status: implemented in current V2 full slice.

### Leap 3: SpeckitPreworkMachine

Status: implemented in current V2 full slice.

### Leap 4: V2 runner migration

Status: partially implemented through `scripts/hldspec_v2.py`; legacy wrappers remain reference/compatibility only.

### Leap 5: Flow test readiness

Status: implemented by `scripts/hldspec_v2_flow_test.py`.

## Remaining next leaps

```text
SourceUpdateMachine
SpecBoundaryMachine
RunSkepticReviewMachine
ConstitutionQualityMachine
V2 runner migration
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

## What not to do

```text
- do not keep patching old shell wording
- do not build thin adapters with no product value
- do not delete all tests without replacements
- do not run old brittle tests as active V2 gates
- do not invoke SpecKit prematurely
- do not spend paid agent credits on deterministic local commands
```

## Apply-step debug requirement

`ApplyHldConversionMachine` must preserve legacy apply-script stdout/stderr.

Debug artifacts:

```text
workspace/.specify/sync/apply_hld_conversion_command.json
workspace/.specify/sync/apply_hld_conversion_command.md
```

`KEEP_AS_ONE` decisions must include `approved_keep_reason`.
