# HLDspec ProjectMachine V2

## Purpose

`ProjectMachine` is the top-level HLDspec V2 coordinator.

It coordinates smaller state machines. It must not own detailed gate policy.

## Current implemented slice

```text
ProjectMachine
  -> RawHldConversionMachine
```

## Contract

`ProjectMachine` receives `MachineContext`:

```text
repo_root
source_hld
workspace
metadata
```

It returns `MachineResult`.

## State handling

```text
RawHldConversionMachine STOP_CHECKPOINT
  -> ProjectMachine STOP_CHECKPOINT

RawHldConversionMachine BLOCKED
  -> ProjectMachine BLOCKED

RawHldConversionMachine ERROR
  -> ProjectMachine ERROR

RawHldConversionMachine CONTINUE
  -> ProjectMachine CONTINUE / RAW_HLD_CONVERSION_READY_TO_APPLY

RawHldConversionMachine DONE
  -> ProjectMachine CONTINUE / RAW_HLD_CONVERSION_COMPLETE
```

## V2 CLI

```bash
uv run python scripts/hldspec_v2.py ./Flow-System-HLD.md .hldspec-v2-run
```

Exit codes follow the shared state-machine contract:

```text
0 = OK / continue
1 = tool error
2 = human checkpoint required
3 = gate blocked
4 = unsafe action attempted
```

## Non-goals

```text
- does not invoke SpecKit
- does not modify source HLD
- does not run legacy scripts
- does not implement application code
```

## Next machines

```text
SpecBuildPlanMachine
SpeckitPreworkMachine
ApprovalGateMachine
SourceUpdateMachine
```
