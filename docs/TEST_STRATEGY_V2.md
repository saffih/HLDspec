# HLDspec Test Strategy V2

made by AI

## Decision

Tests must move from implementation-string assertions to behavioral contracts.

## Current problem

Some legacy tests check exact strings in shell scripts.

That is useful as temporary compatibility coverage, but it is not enough for architecture quality.

Bad long-term test pattern:

```text
assert "Continuation protocol:" in project_continue.sh
assert "SpecKit prework approval gate" in project_continue.sh
```

Better test pattern:

```text
given machine state and artifacts
when the machine runs
then MachineResult has expected status, checkpoint, artifacts, and forbidden actions
```

## Test layers

### Contract tests

Verify shared data contracts:

```text
MachineResult
Checkpoint
HumanQuestion
ArtifactRef
ExitCode
```

### Machine transition tests

Verify state transitions:

```text
NO_WORKSPACE -> RAW_HLD_READONLY_DONE
RAW_HLD_READONLY_DONE -> HLD_CONVERSION_DECISIONS
HLD_CONVERSION_DECISIONS with TBD -> STOP_CHECKPOINT
HLD_CONVERSION_DECISIONS answered -> WORKING_HLD_CONVERTED
bad plan -> SPEC_BUILD_PLAN_CHECKPOINT
good plan + prework rework -> SPECKIT_PREWORK_REWORK
good plan + good prework -> SPECKIT_PREWORK_APPROVAL_GATE
```

### Renderer tests

Verify output shape:

```text
Current checkpoint:
Blocking reason:
Human decision needed:
Controlling artifacts:
Continuation protocol:
What is not modified / not invoked:
```

### CLI adapter tests

Verify scripts pass arguments correctly and preserve exit codes.

### Legacy compatibility tests

Keep only while migration is incomplete.

Delete a legacy test only in the same patch that adds a stronger V2 behavior test.

## Deletion policy

Do not delete all tests.

Allowed deletion:

```text
legacy brittle test removed
stronger V2 contract/behavior test added
full suite passes
same commit
```

Not allowed:

```text
delete tests/
rewrite everything
hope it works
```

## Readiness rule

The V2 rewrite is not ready until:

```text
- full legacy suite passes
- V2 contract tests pass
- ready gate passes
- Flow reaches a clear checkpoint
- checkpoint output asks the real human question
```
