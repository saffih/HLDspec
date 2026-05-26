# HLDspec Development Handoff

## Purpose

This document defines how to hand off work while developing the HLDspec repo itself.

This is different from target-product handoff.

- Target-product handoff: HLDspec prepares `target/` for SpecKit and target agents.
- HLDspec development handoff: one developer/model/agent hands the HLDspec repo work to another.

## Core rule

A new model must not depend on hidden chat history.

Every HLDspec development handoff must provide:

- current repo state
- current task/focus
- files changed or intended to change
- architecture context
- relevant invariants
- tests already run
- tests still required
- RunSkeptic status
- open ACTION/CONFLICT items
- next safe step

## Statelessness rule

HLDspec core remains stateless.

Development handoff packets are runtime artifacts, not product state.

Default generated location:

```text
.hldspec-dev/handoff/
  HANDOFF.md
  HANDOFF.json
```

`.hldspec-dev/` is gitignored.

If a handoff decision becomes durable project knowledge, promote it into one of:

```text
CLAUDE.md
TASKS.md
docs/DOCS_INDEX.md
docs/ARCHITECTURE_V2.md
docs/CANONICAL_FLOW.md
docs/HLDSPEC_STABILITY_ARCHITECTURE.md
```

## Required first-read set

Every model starting work on HLDspec must read:

```text
CLAUDE.md
TASKS.md
docs/DOCS_INDEX.md
docs/CANONICAL_FLOW.md
docs/ARCHITECTURE_V2.md
docs/HLDSPEC_STABILITY_ARCHITECTURE.md
```

Read additional docs only when relevant to the task.

## Model roles for HLDspec development

| Tier | Use for | Must not do |
|---|---|---|
| MODEL_ROUTINE | file inventory, status, deterministic extraction, summary | architecture or promotion decisions |
| MODEL_DEFAULT | focused repo edits, tests, small docs/code changes | approve architecture or source-of-truth changes |
| MODEL_STRONG | bounded refactors, adapter seams, new validators, tests | unresolved architecture conflicts |
| MODEL_CRITICAL | architecture, contracts, source-of-truth, gate semantics, RunSkeptic verdicts | broad edits without decomposition |
| HUMAN | unresolved product intent, approvals, tradeoffs, risky transitions | hidden approval |

Rule:

```text
Weakest sufficient model creates.
Strongest necessary model promotes.
```

## Handoff packet fields

A proper HLDspec development handoff includes:

```text
handoff_id:
created_at:
repo:
from_actor:
to_actor:
model_tier:
focus:
current_branch:
current_head:
git_status:
last_commits:
required_first_read:
changed_files:
relevant_files:
invariants:
tests_run:
tests_required:
runskeptic_status:
open_actions:
open_conflicts:
next_safe_step:
do_not_do:
```

## Required invariants

Every handoff must repeat these invariants:

1. Source HLD is read-only. Workspace copy only.
2. SpecKit is not invoked until approval gates pass.
3. Final SpecKit specs are not written manually by HLDspec.
4. Application code is not implemented by HLDspec.
5. Gate machines gate; scripts generate.
6. Dependency graph and invocation queue must not diverge.
7. RunSkeptic must use the real current `skeptic.md`.
8. Patch scripts must be syntax checked before handoff.
9. Dirty-tree work must be handled explicitly.
10. HLDspec runtime state belongs outside core code.

## RunSkeptic handoff rule

Use RunSkeptic before or during handoff when work touches:

- architecture
- contracts
- gates
- source of truth
- dependency graph
- SpecKit invocation
- model routing
- prompt/delegation policy
- target workspace layout
- state/event/log ownership
- safety rules

If RunSkeptic finds ACTION, list the fix plan.

If RunSkeptic finds CONFLICT, stop and ask for a decision.

## What handoff must prevent

The handoff must prevent:

- model B repeating model A's discovery work
- hidden assumptions becoming architecture
- stale docs becoming source of truth
- scripts becoming hidden workflow owners
- partial patches being rerun blindly
- target-product rules being confused with HLDspec-development rules
- broad context dumping into weaker models

## Development handoff command

Generate a handoff packet:

```bash
python3 scripts/hldspec_dev_handoff.py \
  --focus "TargetWorkspaceAdapter follow-up" \
  --from-agent codex \
  --to-agent claude \
  --model-tier MODEL_STRONG
```

Default output:

```text
.hldspec-dev/handoff/HANDOFF.md
.hldspec-dev/handoff/HANDOFF.json
```

## Acceptance criteria

Development handoff is proper when another model can continue the HLDspec repo work without reading the full conversation and without guessing:

- what changed
- what was intended
- what must not be touched
- which docs are authoritative
- which tests prove the work
- what the next safe step is
