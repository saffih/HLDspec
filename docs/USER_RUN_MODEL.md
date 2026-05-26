# User Run Model

## Purpose

This document defines the simple user workflow for HLDspec.

The user should not need to understand internal scripts to start.

## Canonical command surface

Current public product commands:

| Command | Status | Notes |
|---|---|---|
| `hldspec start` | current | Prepare or resume a target session. |
| `hldspec status` | current | Show target session status. |
| `hldspec review` | current | Show human-relevant review files. |
| `hldspec continue` | current | Run ProjectMachine to the next safe checkpoint. |
| `hldspec diff` | current | Compare source hash with recorded target source hash. |
| `hldspec doctor` | current | Check repo and target session prerequisites. |

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
- write an agent start prompt
- write a tool manifest
- detect create/update/adopt/resume intent
- print the next safe action

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
`continue`, `diff`, and `doctor`. Today, `hldspec continue` advances the
ProjectMachine to the next safe checkpoint and blocks before unapproved SpecKit
work.

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
