# Agent bootstrap for this repo

made by AI

## HLDspec trigger

When a user prompt starts with:

```text
HLDspec /path/to/HLD.md
```

or:

```text
HLDspec /path/to/HLD.md --workspace /path/to/workspace
```

do not guess the process from memory.

Do this first:

```bash
cd /Users/saffi/code/HLDspec
bash scripts/hldspec_agent_start.sh <source-HLD.md> [--workspace <workspace>] --print-context
```

Then follow the generated context exactly.

## Hard rules

- Do not search the web for this workflow.
- Do not search unrelated memory/docs before reading the generated context.
- Treat the source HLD as read-only.
- Work only on workspace copies.
- Do not invoke SpecKit.
- Do not create final specs manually.
- Do not implement.
- Do not answer human checkpoint questions silently.
- Do not promote artifacts without judge approval.

## Stage rule

If the generated context says:

```text
CONVERSION_READY_TO_APPLY
```

then the next step is conversion of the workspace HLD copy.

Do not rerun `first_run_readonly.sh` yet.

Convert only the workspace `HLD.md` using:

- workspace `HLD.raw.md`
- recorded conversion decisions
- conversion plan
- raw marking plan

After conversion, then run the next read-only flow if the generated context says it is safe.

## Stage rule: SpecKit-ready prework

Before invoking SpecKit, an agent must produce and review:

```bash
bash scripts/hldspec_speckit_ready.sh <workspace>
```

This builds:

- architecture analysis
- compact constitution context
- bottom-up spec list
- readiness review

It does not invoke SpecKit, create final specs, or implement.
