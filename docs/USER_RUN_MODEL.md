# User Run Model

## Purpose

This document defines the simple user workflow for HLDspec.

The user should not need to understand internal scripts to start.

## Public user interface (agent-first)

The public HLDspec user interface is **a one-line instruction to an agent**, not
direct script execution. The user gives an agent a short instruction; the agent
uses HLDspec's command/tool surface internally; the user receives **STATUS,
blockers, evidence, and the next safe action** — not script mechanics.

Copy-ready instruction to give the agent:

```text
Use HLDspec with source HLD: <path-to-HLD.md> and target project: <path-to-target>. Prepare the target, check SpecKit readiness, and report STATUS, blockers, evidence, and next safe action. Do not implement or run SpecKit unless HLDspec says it is safe.
```

In this agent-first model the user sees results, not script paths. The command
surface below is the **internal tool surface** the agent (or a maintainer)
invokes; it is documented for reference, not as the primary human UX.

## Command surface

The canonical command surface is defined in
[`HLDSPEC_TERMINOLOGY_AND_FLOW.md`](HLDSPEC_TERMINOLOGY_AND_FLOW.md) (HLDspec
Product Facade); this doc presents the same set as the internal tool surface the
agent runs for the user.

Current public product commands:

| Command | Status | Notes |
|---|---|---|
| `hldspec start` | current | Prepare or resume a target session. |
| `hldspec status` | current | Show target session status. |
| `hldspec review` | current | Show human-relevant review files. |
| `hldspec continue` | current | Run ProjectMachine to the next safe checkpoint. |
| `hldspec diff` | current | Compare source hash with recorded target source hash. |
| `hldspec doctor` | current | Check repo and target session prerequisites. |
| `hldspec speckit-doctor` | current | Check target-level SpecKit readiness and next actions. |
| `hldspec operator-state` | current | Show the readiness-boundary Operator State and the next safe action. |
| `hldspec speckit-state` | current | Alias of `operator-state`. |

Future product commands:

| Command | Status | Notes |
|---|---|---|
| `hldspec interview` | future | Collect missing source, target, intent, and constraints. |
| `hldspec prework` | future | Generate use-case/API map, packages, graph, queue, and context packs. |
| `hldspec speckit` | future | Delegate one approved SpecKit phase from bounded evidence. |
| `hldspec pause` | future | Record a user-requested pause/checkpoint. |

Legacy/debug commands:

| Command or path | Status | Notes |
|---|---|---|
| `hldspec run` | legacy/debug | Older product runner name. |
| `hldspec speckit-proxy` | legacy/debug | Older proxy naming. |
| direct low-level scripts | legacy/debug | Maintainer/debug tools, not normal user workflow. |

## One-command start

```bash
hldspec start --source ./HLD.md --target ./target
```

Optional:

```bash
hldspec start \
  --source ./HLD.md \
  --target ./target \
  --agent devin \
  --comment "update from changed HLD, preserve existing SpecKit work"
```

## What start does

`hldspec start` prepares an agent session.

It should:

- create target directory if needed
- preserve the source HLD under `target/targetHLD/raw/`
- create or preserve `target/targetHLD/HLD.md`
- write an agent session record
- write interview artifacts under `target/.hldspec/interview_answers.json` and `.md`
- write an agent start prompt
- write a tool manifest
- detect create/update/adopt/resume intent
- print the next safe action

The interview artifacts record the source path and hash, target path, detected
mode, selected agent, user comment, simple intent classification, approval
expectations when stated, constraints, and open questions. They are durable
target-product state and must be written only under `target/`.

## Normal flow

```text
hldspec start
  -> hldspec status
  -> hldspec review
  -> hldspec continue
```

## Status

```bash
hldspec status --target ./target
```

Shows:

- current detected mode
- source hash
- target state
- next safe action
- blockers
- review files
- generated prompt location

## Review

```bash
hldspec review --target ./target
```

Shows only human-relevant checkpoint material:

- constitution plan
- backend technology recommendation
- design principle selection
- spec package plan
- dependency graph
- RunSkeptic findings
- unresolved conflicts

## Continue

```bash
hldspec continue --target ./target
```

Continues the next safe HLDspec step through the agent/tool plan.

It must not silently skip review gates.

## Future SpecKit Command

```bash
hldspec speckit --target ./target --next
```

Future command. The current product facade is `start`, `status`, `review`,
`continue`, `diff`, `doctor`, `speckit-doctor`, and `operator-state` (alias
`speckit-state`). Today, `hldspec continue` advances the ProjectMachine to the
next safe checkpoint and blocks before unapproved SpecKit work.

SpecKit owns:

- spec.md
- clarify
- plan.md
- research.md
- data-model.md
- contracts/
- quickstart.md
- tasks.md
- implementation

## Diff

```bash
hldspec diff --source ./HLD.md --target ./target
```

Shows whether source/resources changed compared to the recorded session.

## Doctor

```bash
hldspec doctor --target ./target
```

Checks that required docs, scripts, target directories, and session files exist.

## User intent comments

The user may add comments:

```bash
hldspec start \
  --source ./HLD.md \
  --target ./target \
  --comment "upgrade prompts only; do not change package order"
```

The agent must classify the comment and stop if the comment conflicts with target state.

## Safety rules

- Source HLD/resources are read-only evidence.
- `target/` is the working product workspace.
- Scripts are tools for agents.
- Human decisions stay explicit.
- RunSkeptic runs at key junctions.
- Missing evidence is ACTION or CONFLICT, not PASS.

## Bounded SpecKit prompt generation

Maintainer/debug tool:

```bash
scripts/build_speckit_context_prompts.py <target>
```

This generates context economy artifacts and bounded SpecKit phase prompts under the target workspace. It is not a public command yet; future product flow should expose this through a guarded `hldspec prework` or `hldspec speckit` path after validators and promotion gates are complete.

## Context prompt validation

Maintainer/debug tool:

```bash
scripts/validate_hldspec_target.py <target>
```

This validates generated context economy artifacts and bounded SpecKit prompts, including RunSkeptic triggers, model tiers, broad-read phrasing, and implement-phase human approval guards. It writes reports under `target/.hldspec/validation/`. It is not a public command.

## Promotion gate

Maintainer/debug readiness check:

```bash
scripts/check_hldspec_promotion_gate.py <target>
```

This reads available target validation reports and readiness artifacts, then writes `target/.hldspec/validation/promotion_gate.json` and `.md`. Promotion requires gate status `PASS`; ACTION or CONFLICT findings block readiness promotion. It is an internal guarded check, not a public command.
