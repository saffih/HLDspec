# User Run Model

## Purpose

This document defines the simple user workflow for HLDspec.

The user should not need to understand internal scripts to start.

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
  -> hldspec speckit --next
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

## SpecKit

```bash
hldspec speckit --target ./target --next
```

Runs or prepares the next approved SpecKit delegation.

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
