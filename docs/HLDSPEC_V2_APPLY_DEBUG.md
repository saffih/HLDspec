# HLDspec V2 Apply Debug

made by AI

## Problem

The legacy apply script prints validation failures to stdout and returns `2`.

V2 must not hide that output.

## V2 behavior

`ApplyHldConversionMachine` now writes command debug artifacts:

```text
workspace/.specify/sync/apply_hld_conversion_command.json
workspace/.specify/sync/apply_hld_conversion_command.md
```

If the legacy apply script returns `2`, V2 treats it as:

```text
status = BLOCKED
state = APPLY_REFUSED
```

not as a tool crash.

## Common reason

`KEEP_AS_ONE` requires an approved keep reason.

Use:

```bash
uv run python scripts/hldspec_v2_answer_conversion_queue.py \
  ~/code/flow/.hldspec-v2-flow-test/workspace/.specify/sync/hld_conversion_decision_queue.json \
  --answer Q-001=SPLIT_AS_PROPOSED \
  --answer Q-002=SPLIT_AS_PROPOSED \
  --answer Q-003=KEEP_AS_ONE \
  --keep-reason "Q-003=Milestones are planning context, not a standalone spec boundary."
```

Then rerun:

```bash
uv run python scripts/hldspec_v2_flow_test.py ~/code/flow/Flow-System-HLD.md
```
