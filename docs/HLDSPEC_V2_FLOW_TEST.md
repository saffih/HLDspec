# HLDspec V2 Flow Test

made by AI

## Purpose

This is the no-SpecKit Flow readiness test for HLDspec V2.

It runs the V2 state-machine workflow against a source HLD and writes test artifacts.

## Command

From the HLDspec repo:

```bash
uv run python scripts/hldspec_v2_flow_test.py ~/code/flow/Flow-System-HLD.md
```

or:

```bash
scripts/hldspec_v2_flow_test.sh ~/code/flow/Flow-System-HLD.md
```

## Output

Default output directory:

```text
~/code/flow/.hldspec-v2-flow-test/
```

Generated artifacts:

```text
machine_result.json
machine_result.md
flow_test_summary.json
flow_test_summary.md
workspace/
```

## Valid outcomes

A checkpoint is a valid test result.

```text
CHECKPOINT_REACHED
  state machine stopped safely and asks a real human question

FLOW_CONTINUES
  machine can continue or completed a safe stage

BLOCKED
  a gate or required artifact is missing

ERROR
  tooling or unsafe behavior failed
```

## Safety contract

The Flow test runner must not:

```text
- invoke SpecKit
- modify the source HLD
- write final specs manually
- implement app code
```

Machine-readable safety values:

```text
SpecKit invoked: false
Source HLD modified by runner: false
App code implemented: false
```

The runner may modify only its workspace:

```text
.hldspec-v2-flow-test/workspace/
```

## When this is ready

Ready for real Flow testing when:

```text
uv run python -m unittest discover -s tests_v2 -v
uv run python scripts/hldspec_v2_ready_gate.py --repo . --output-dir .hldspec-v2-ready-gate --fail-on-not-ready
uv run python scripts/hldspec_v2_flow_test.py ~/code/flow/Flow-System-HLD.md
```

The expected first real Flow outcome is usually:

```text
CHECKPOINT_REACHED
```

with a specific checkpoint and human decision needed.
