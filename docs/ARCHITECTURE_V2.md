# HLDspec Architecture V2

> Canonical system model, terminology, ownership boundaries, and full flow:
> [`HLDSPEC_TERMINOLOGY_AND_FLOW.md`](HLDSPEC_TERMINOLOGY_AND_FLOW.md). This doc
> describes the code-level engine; the canonical doc wins on any terminology or
> flow conflict.

HLDspec V2 is a state-machine workflow engine.

## Implemented V2 slice

```text
scripts/hldspec_v2.py
  -> ProjectMachine
     -> RawHldConversionMachine
     -> ApplyHldConversionMachine
     -> SpecBuildPlanMachine
     -> SpeckitPreworkMachine
     -> ApprovalGateMachine
```

## Core contracts

```text
MachineResult
Checkpoint
HumanQuestion
ArtifactRef
MachineContext
```

## Active test layout

```text
tests_v2/ = active V2 contract and machine tests
tests_legacy/ = preserved legacy tests, not active during V2 rewrite
```

## Safety

```text
- source HLD is never modified implicitly
- working HLD is the only conversion target
- SpecKit is blocked until approval
- app code is not implemented by HLDspec V2 machines
```
