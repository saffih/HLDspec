# HLDspec V2 Spec Plan Debug

made by AI

## Purpose

When `SpecBuildPlanMachine` blocks, the user needs actionable details, not only counters.

The machine now writes:

```text
workspace/firstrun/.specify/sync/spec_build_plan_quality_debug.json
workspace/firstrun/.specify/sync/spec_build_plan_quality_debug.md
```

## Blocking checkpoint

A non-green plan becomes:

```text
checkpoint = SPEC_BUILD_PLAN_CHECKPOINT
status = STOP_CHECKPOINT
```

The checkpoint asks for one explicit decision:

```text
FIX_PLAN
ACCEPT_WITH_RATIONALE
STOP_FOR_MANUAL_REDESIGN
```

## Why

The system should not silently continue into SpecKit when planned specs are flagged.

It also should not hide which specs are problematic.

## Safety

```text
- Do not invoke SpecKit.
- Do not implement app code.
- Review flagged planned specs first.
```

## Flow command

After a blocked Flow run:

```bash
cat ~/code/flow/.hldspec-v2-flow-test/workspace/firstrun/.specify/sync/spec_build_plan_quality_debug.md
cat ~/code/flow/.hldspec-v2-flow-test/workspace/firstrun/.specify/sync/spec_build_plan_review.md
```
