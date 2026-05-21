# HLDspec Default Invocation

made by AI

Every project-level HLDspec invocation uses the judge/orchestrator role by default.

## Minimal user prompt

```text
HLDspec ./Flow-System-HLD.md
```

Replace `./Flow-System-HLD.md` with the project HLD path.

## Default agent contract

When the user invokes HLDspec on an HLD, the external coding agent must act as the HLDspec judge/orchestrator.

The agent runs:

```bash
~/code/HLDspec/scripts/hldspec_run.sh <path-to-HLD.md>
```

The agent continues only to the next safe checkpoint.

## Always true

- Do not modify the source HLD.
- Work inside `.hldspec-first-run` unless the human explicitly approves another path.
- Ask the human only at generated HLDspec human checkpoints.
- Do not answer human checkpoint questions yourself.
- Do not create specs, tasks, downstream analysis, or implementation unless the HLDspec gate allows it and the human approves the write step.
- Report briefly: what was run, what happened, checkpoint reached, and what decision is needed if any.

## If uv cache is sandbox-blocked

Use project-local cache:

```bash
UV_CACHE_DIR="$PWD/.hldspec-uv-cache" ~/code/HLDspec/scripts/hldspec_run.sh <path-to-HLD.md>
```

## Checkpoint continuation protocol

When HLDspec stops at a human checkpoint, the human only answers the listed questions.

The agent must then:

1. update the generated checkpoint JSON with the human answers
2. preserve the checkpoint artifact as the source of truth
3. rerun the exact same HLDspec command
4. report the next checkpoint

For conversion checkpoints, update:

```text
.hldspec-first-run/.specify/sync/hld_conversion_decision_queue.json
```

Then rerun:

```bash
~/code/HLDspec/scripts/hldspec_run.sh <path-to-HLD.md>
```

The human should not need to provide this process again.

## Decision source-of-truth rule

Human checkpoint answers must be recorded in:

```text
.specify/sync/hld_decision_log.json
.specify/sync/hld_decision_log.md
.specify/sync/hld_source_decision_appendix.md
```

Do not apply the appendix to the source HLD unless the human explicitly approves that source-HLD write.


## Source-HLD update queue

Some checkpoint answers may affect source HLD content or structure.

Review:

```text
.specify/sync/hld_source_update_queue.md
```

If the queue has items, report them as possible source-HLD updates and ask for explicit approval before modifying the source HLD.

## Spec Build Plan checkpoint

If target-spec generation is blocked, review:

```text
.specify/sync/spec_build_plan_decision_queue.md
```

The judge/orchestrator may explain its recommendation, but the human must answer the decision queue before any target-spec generation or HLD-SPECS remapping.

## Target Spec Work Order

If target-spec generation is allowed, review:

```text
.specify/sync/target_spec_work_order.md
```

Follow the bottom-up order in that artifact. Do not jump to a nearby feature cluster unless the human explicitly changes the order.
