# First Run: Read-Only HLDspec Cycle

made by AI

Use this when you want to test a real HLD through the safe read-only HLDspec cycle.

## Command

```bash
bash scripts/first_run_readonly.sh /path/to/HLD.md
```

Optional explicit workspace:

```bash
bash scripts/first_run_readonly.sh /path/to/HLD.md /tmp/my-hldspec-first-run --force
```

## What it runs

```text
HLD.raw.md / HLD.md copy
-> HLD format report
-> HLD map
-> Spec Build Plan
-> Plan Quality Gate
-> Spec Build Plan Review
```

## Safety

The first-run script:

- does not modify the source HLD
- does not call an agent
- does not create specs
- does not create `.specify/memory/constitution.md`
- writes only inside the chosen workspace

## Main files to inspect

```text
logs/hld_spec_sync/<timestamp>/hld_format_report.md
.specify/sync/hld_index.md
.specify/sync/spec_build_plan.md
.specify/sync/spec_build_plan_review.md
.specify/sync/spec_build_plan.json
```

## How to interpret the result

### KEEP_PLAN

The plan is internally coherent for read-only review.

### REVIEW_PLAN

The plan has concerns but may be fixed by clarifying HLD metadata or expectations.

### SPLIT_PLANNED_SPEC

The plan likely grouped too much into one spec. Typical causes:

- mixed layers
- mixed HLD roles
- API + processing in one spec
- operations/recovery + processing in one spec
- explicit `HLD-SPECS` mapping groups unrelated sections

### RESOLVE_CONFLICT

A conflict must be decided before moving forward.


## Target-spec context note

The Spec Build Plan Review does not mean one HLD section becomes one spec.

The review tells you which HLD sections are related to each planned spec. When target-spec support exists, each target spec should be generated from the plan plus those explicitly related full HLD sections, not from the whole HLD and not from summaries alone.

Section Cards, if introduced later, are routing/context-control aids only. They help decide what full source evidence to fetch. They do not replace the full HLD section text.

## Current boundary

This is the full current safe cycle.

Do not proceed to `--target-spec` yet. Target-spec generation should come only after the Spec Build Plan review is clean or explicitly accepted.
