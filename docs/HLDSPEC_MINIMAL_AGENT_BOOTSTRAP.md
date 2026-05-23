# HLDspec Minimal Agent Bootstrap

made by AI

## Purpose

Make the minimal trigger reliable for cheap/small agents.

The user-facing prompt should stay small:

```text
HLDspec /absolute/path/to/HLD.md --workspace /path/to/workspace
```

The agent must expand it internally by reading repo bootstrap rules and the generated start context.

## Required first action

For any `HLDspec ...` trigger, the agent must run:

```bash
cd /Users/saffi/code/HLDspec
bash scripts/hldspec_agent_start.sh <source-HLD.md> [--workspace <workspace>] --print-context
```

Then follow the generated context.

## Do not do first

- do not search the web
- do not search generic memory
- do not rerun `first_run_readonly.sh`
- do not edit the source HLD
- do not invoke SpecKit
- do not implement

## Conversion-ready rule

If the generated context says:

```text
current stage: CONVERSION_READY_TO_APPLY
```

then:

```text
next action = convert the workspace HLD copy
```

Not:

```text
rerun first_run_readonly on raw source HLD
```

## Correct behavior at CONVERSION_READY_TO_APPLY

Use:

```text
workspace/HLD.raw.md
workspace/HLD.md
workspace/.specify/sync/hld_conversion_decision_queue.json
workspace/.specify/sync/hld_conversion_plan.md/json
workspace/.specify/sync/raw_hld_marking_plan.md/json
```

Convert:

```text
workspace/HLD.raw.md -> workspace/HLD.md
```

Then run the read-only flow only after conversion is complete.
