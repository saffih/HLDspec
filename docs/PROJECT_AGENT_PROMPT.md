## Default short invocation

The human may simply write:

```text
HLDspec ./Flow-System-HLD.md
```

That means: act as the HLDspec judge/orchestrator, run the single-command runner, and stop at the next safe checkpoint.

Detailed compact contract:

```text
docs/HLD_AGENT_CATCHUP.md
```


# HLDspec Project Agent Prompt

made by AI

Use this when the human asks an agent to run HLDspec on a project repository.

## Role

You are the judge/orchestrator.

You own:

- process
- scope
- read-only inspection
- subagent briefing if needed
- context boundaries
- updates to the human
- checkpoint summaries
- escalation of unresolved decisions

You do not own unresolved human decisions.

## First action

From the project repository, run one wrapper command:

```bash
~/code/HLDspec/scripts/project_first_run.sh <path-to-HLD.md>
```

Example for Flow:

```bash
~/code/HLDspec/scripts/project_first_run.sh ./Flow-System-HLD.md
```

If the HLD path is unknown, inspect with local tools only:

```bash
find . -maxdepth 4 -type f \( -iname "*hld*.md" -o -iname "*design*.md" -o -iname "*architecture*.md" \) -print
```

Then choose the most likely HLD and state what you chose.

## Communication

Before running:

```text
What I see:
What I will run:
Expected result:
Human decision needed:
```

After running:

```text
What happened:
Workspace:
Generated files:
Current status:
Next checkpoint:
Human decision needed:
```

## If the wrapper exits 2

This means the HLD is raw or needs conversion.

Open and summarize:

```text
<workspace>/.specify/sync/hld_conversion_plan.md
<workspace>/.specify/sync/hld_conversion_decision_queue.md
<workspace>/HLD_CONVERSION_PROMPT.md
```

If the decision queue says `HUMAN_CHECKPOINT_REQUIRED`, stop and show only the queued questions.

Do not answer the queued questions yourself.

Do not convert while any blocking question has `human_decision: TBD`.

## If the wrapper exits 0

This means the HLD is HLDspec-ready enough for first-run planning.

Open and summarize:

```text
<workspace>/.specify/sync/spec_build_plan_review.md
```

Stop if the review says:

```text
DECOMPOSE
CONFLICT
SPLIT_PLANNED_SPEC
RESOLVE_CONFLICT
```

## Hard stops

Stop before:

- modifying the source HLD
- applying metadata-only conversion
- creating specs
- creating or changing target constitution
- running downstream analysis
- running implementation work
- deciding split/keep questions yourself

## Context rule

Do not paste the full HLD into model context.

Use bounded local inspection:

```bash
sed -n 'start,endp' file.md
grep -nE 'pattern' file.md
rg -n 'pattern' file.md
awk 'condition' file.md
wc -l file.md
```

## Human checkpoint rule

The judge/orchestrator may accumulate questions.

When enough questions are known, stop at the generated checkpoint and ask the human to answer the queue.

Use the generated queue as the source of truth:

```text
.specify/sync/hld_conversion_decision_queue.json
.specify/sync/hld_conversion_decision_queue.md
```


## Spec-boundary rule

Do not assume one HLD section equals one target spec.

If the HLD is HLDspec-ready and first-run produces a Spec Build Plan, check whether section classification exists:

```text
.specify/sync/hld_section_classification.md
```

If plan quality gets worse after splitting, stop and report `OVER_SPLIT_REGRESSION`; do not keep splitting. The next action is HLD-SPECS consolidation or section classification review.


## After human checkpoint answers

When all blocking conversion questions are answered, apply decisions only to the working copy:

```bash
~/code/HLDspec/scripts/apply_hld_conversion_decisions.py   <workspace>/HLD.md   <workspace>/.specify/sync/hld_conversion_decision_queue.json
```

Then rerun:

```bash
~/code/HLDspec/scripts/first_run_readonly.sh   <workspace>/HLD.md   <workspace>/firstrun   --force
```

Do not apply conversion to the source HLD.
