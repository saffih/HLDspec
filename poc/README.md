# HLDspec POC Playground

made by AI

This directory provides tiny fake HLDs for a fast learning cycle.

Goal:

```text
fake HLD
-> first_run_readonly.sh
-> Spec Build Plan
-> Plan Quality Gate
-> Spec Build Plan Review
```

Safety:

- no agent call
- no specs created
- no target `.specify/memory/constitution.md` created
- outputs go to `/tmp/hldspec-poc` by default

## Run all POC cases

```bash
bash poc/run_poc.sh
```

Optional output directory:

```bash
bash poc/run_poc.sh /tmp/my-hldspec-poc
```

## Cases

### 01_clean_hld.md

Expected learning:

- separate capabilities
- low boundary risk
- likely `FIX / KEEP_PLAN`

### 02_split_needed_hld.md

Expected learning:

- one planned spec groups API + processing + failure recovery
- should be flagged for split/review
- likely `DECOMPOSE / SPLIT_PLANNED_SPEC`

### 03_conflict_hld.md

Expected learning:

- explicit conflict refs must block generation
- likely `CONFLICT / RESOLVE_CONFLICT`

## What to inspect

For each case:

```text
/tmp/hldspec-poc/<case>/.specify/sync/spec_build_plan_review.md
/tmp/hldspec-poc/<case>/.specify/sync/spec_build_plan.md
/tmp/hldspec-poc/<case>/.specify/sync/spec_build_plan.json
```

## Beskeptic use

Use the POC to test changes before touching a real project HLD.

If a planned future change cannot explain these three cases, do not advance it.
