# HLDspec Architecture V2

made by AI

## Decision

HLDspec must be rebuilt around explicit state-machine contracts.

The goal is not another thin script patch. The goal is a stable architecture that can support:

```text
- raw HLD conversion
- product/architecture marking
- plan quality gates
- SpecKit prework
- human checkpoints
- source-HLD safety
- RunSkeptic review
- future agent orchestration
```

## Core principle

HLDspec is a workflow engine.

Workflow engines should expose states, transitions, guards, actions, artifacts, and checkpoints explicitly.

## Target architecture

```text
hldspec/
  state_machine.py
  artifacts.py
  command_runner.py
  checkpoints.py
  result_renderer.py
  machines/
    project.py
    raw_hld_conversion.py
    spec_build_plan.py
    speckit_prework.py
    approval_gate.py
    source_update.py
    ready_gate.py
    runskeptic_review.py
    constitution_quality.py
```

## Script boundaries

```text
scripts/hldspec_run.sh
  compatibility wrapper only

scripts/project_continue.sh
  compatibility wrapper only

scripts/hldspec_continue.py
  CLI adapter for the project state machine

scripts/render_hldspec_checkpoint.py
  CLI adapter for checkpoint rendering

scripts/hldspec_ready_gate.py
  readiness gate adapter
```

## MachineResult contract

Every machine returns a result with:

```text
machine
state
status
checkpoint
actions_run
artifacts_written
errors
```

Allowed statuses:

```text
CONTINUE
STOP_CHECKPOINT
BLOCKED
DONE
ERROR
```

Exit-code mapping:

```text
0 = OK / done / continue
1 = tool error
2 = human checkpoint required
3 = gate blocked
4 = unsafe action attempted
```

## Checkpoint contract

Every checkpoint must include:

```text
kind
blocking_reason
human_questions
controlling_artifacts
next_action
forbidden_actions
```

Every rendered checkpoint must include:

```text
Current checkpoint:
Blocking reason:
Human decision needed:
Controlling artifacts:
Continuation protocol:
What is not modified / not invoked:
```

## Sub-machine responsibilities

### ProjectMachine

Coordinates sub-machines. Does not own detailed gate logic.

### RawHldConversionMachine

Owns:

```text
- raw/converted HLD detection
- conversion decision queue inspection
- open human questions
- conversion application to the working HLD only
```

Does not own:

```text
- SpecKit
- plan quality
- implementation
- source HLD mutation
```

### SpecBuildPlanMachine

Owns:

```text
- spec_build_plan.json
- spec_build_plan_review.md
- KEEP_PLAN / DECOMPOSE / CONFLICT logic
- flagged planned specs
```

### SpeckitPreworkMachine

Owns:

```text
- constitution update plan
- feature dependency graph
- SpecKit input manifest
- invocation queue
- proxy dossier
- prework package
- prework quality review
```

### ApprovalGateMachine

Owns human approval state and post-approval allowed next action.

### SourceUpdateMachine

Owns source-HLD-affecting updates. Source HLD mutation is a separate risk class and requires explicit approval.

## Uncle Bob / SOLID requirements

```text
SRP: each machine has one reason to change.
OCP: add new checkpoints by adding machine/renderer behavior, not editing shell prose.
DIP: shell wrappers depend on Python CLIs and contracts, not embedded logic.
ISP: each machine has a narrow result contract.
Testability: tests assert state transitions and MachineResult shape.
```

## RunSkeptic requirements

Every architectural finding must include:

```text
observed_evidence
evidence_level
confidence
unknowns
verification
residual_risk
```

## Migration plan

```text
1. Add V2 contracts and tests.
2. Add state-machine primitives.
3. Add MachineResult renderer.
4. Move raw-HLD conversion checkpoint to RawHldConversionMachine.
5. Move plan quality gate to SpecBuildPlanMachine.
6. Move prework quality/approval to SpeckitPreworkMachine and ApprovalGateMachine.
7. Convert shell scripts into thin wrappers.
8. Replace brittle legacy tests only after stronger V2 tests exist.
```

## Non-goals

```text
- Do not delete all legacy tests in one step.
- Do not invoke SpecKit.
- Do not modify source HLDs.
- Do not implement application code.
- Do not rewrite every script in one unverified patch.
```
