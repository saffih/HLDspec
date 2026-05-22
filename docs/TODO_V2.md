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
