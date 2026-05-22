# HLDspec State Machine Contract

made by AI

## Decision

HLDspec is a state-machine system, not a single procedural script.

The next architecture target is:

```text
project_continue.sh
  -> compatibility wrapper only

scripts/hldspec_continue.py
  -> CLI adapter only

hldspec.state_machine
  -> shared state-machine primitives

project machine
  -> top-level coordinator

sub-machines
  -> focused workflow gates/checklists
```

## Why

HLDspec has stages, gates, artifacts, decisions, and stop conditions.

These are state-machine concepts:

```text
state
transition
guard
action
checkpoint
human question
controlling artifact
forbidden action
exit code
```

## Required result contract

Every machine returns a `MachineResult` containing:

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

## Required checkpoint contract

Every checkpoint contains:

```text
kind
blocking_reason
human_questions
controlling_artifacts
next_action
forbidden_actions
```

## Top-level machines

The final architecture should include:

```text
ProjectHldspecMachine
RawHldConversionMachine
SpecBuildPlanMachine
SpeckitPreworkMachine
ApprovalGateMachine
SourceUpdateMachine
ReadyGateMachine
RunSkepticReviewMachine
ConstitutionQualityMachine
```

## Uncle Bob / SOLID rules

```text
SRP: each machine owns one gate/checklist.
OCP: new checkpoint types extend machine/renderer behavior, not shell prose.
DIP: shell wrappers depend on stable Python CLIs and contracts.
ISP: machines expose small result contracts instead of broad ad-hoc dictionaries.
Testability: transition tests assert MachineResult, renderer tests assert output.
```

## Migration rule

Do not rewrite everything in one uncontrolled patch.

Large rewrite is allowed only through staged contract migration:

```text
1. Add state-machine primitives and tests.
2. Add renderer adapter for MachineResult.
3. Move raw-HLD conversion to RawHldConversionMachine.
4. Move spec-plan gate to SpecBuildPlanMachine.
5. Move prework gate to SpeckitPreworkMachine.
6. Convert project_continue.sh to a thin wrapper.
```

Each step must keep full tests green.
