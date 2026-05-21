# Limited Agent Run Card

made by AI

Use this when the agent has limited context/capacity.

This file is the short operational card. Read it before longer docs.

## Mission

Use `~/HLDspec` to process a project HLD while keeping the human able to understand and steer.

Default project example:

```bash
cd /home/sio/embeddedPerformance/simulator
HLD="./Simulator-System-HLD.md"
WORK="$PWD/.hldspec-first-run"
```

## Hard rules

1. Do not load or paste the whole HLD into model context.
2. Use local tools for bounded inspection: `grep`, `rg`, `sed -n`, `awk`, `wc`, `head`, `tail`.
3. Preserve the original HLD. Edit only the working copy inside `$WORK`.
4. Keep the human in the loop.
5. Do not silently continue through `DECOMPOSE`, `CONFLICT`, `SPLIT_PLANNED_SPEC`, or `RESOLVE_CONFLICT`.
6. Do not create or modify specs, target constitution, downstream artifacts, or implementation files without explicit human approval.
7. Do not invent architecture decisions, refs, owners, resources, or spec IDs.

## First command

Run:

```bash
~/HLDspec/scripts/first_run_readonly.sh "$HLD" "$WORK" --force
```

## Interpret result

### Exit code 0

The HLD is HLDspec-ready enough for read-only planning.

Open and summarize:

```bash
sed -n '1,220p' "$WORK/.specify/sync/spec_build_plan_review.md"
```

Report:

```text
Plan Quality decision:
Recommendation:
Planned specs:
Flagged specs:
Conflicts:
Human decision needed:
```

### Exit code 2

The HLD needs conversion first.

Open and summarize:

```bash
sed -n '1,220p' "$WORK/HLD_CONVERSION_PROMPT.md"
```

Then convert `"$WORK/HLD.md"` in batches.

### Any other exit code

Stop and report the error. Do not continue.

## Conversion batch rule

Convert in small batches:

```text
3-5 major sections per batch
```

For very large sections:

```text
inspect internal headings first
explain whether splitting is needed
ask before splitting if interpretation is involved
```

After each batch, report:

```text
Sections converted:
Metadata chosen:
Refs added:
Uncertain fields:
Files changed:
Diff summary:
Next proposed batch:
Human decision needed:
```

Useful commands:

```bash
wc -l "$WORK/HLD.md"
grep -nE '^(#|##|###) ' "$WORK/HLD.md" | head -80
sed -n '120,220p' "$WORK/HLD.md"
rg -n 'REF HLD-|DEPENDS REF|CONFLICTS_WITH|HLD-SPECS|HLD-ROLE' "$WORK/HLD.md"
diff -u "$WORK/HLD.raw.md" "$WORK/HLD.md" | sed -n '1,220p'
```

## Metadata defaults

Use:

```text
HLD-SPECS: TBD
HLD-RESOURCES: TBD
```

unless certain.

Use only supported refs:

```text
REF HLD-xxx
DEPENDS REF HLD-xxx
CONFLICTS_WITH REF HLD-xxx
```

Do not invent refs.

## Required communication format

Before a major step:

```text
What I see:
What it means:
What I plan to do:
Command or edit:
Expected result:
Human decision needed:
```

After a major step:

```text
What happened:
Files created or changed:
What it means:
Next decision:
```

## Stop points

Stop for human decision before:

- accepting `DECOMPOSE` or `CONFLICT`
- splitting major HLD sections
- choosing source of truth
- choosing API/interface ownership
- choosing data/state ownership
- choosing performance/memory constraints
- choosing failure/recovery behavior
- creating/modifying specs
- creating/modifying `.specify/memory/constitution.md`
- creating downstream artifacts
- modifying implementation files

## Minimal success path

```text
1. Run first_run_readonly.sh.
2. If raw, convert HLD.md in bounded batches.
3. Rerun first_run_readonly.sh on the converted HLD.md.
4. Summarize spec_build_plan_review.md.
5. Stop if blocked; ask the human.
```

## Do not proceed to target-spec generation

Target-spec generation is not the default next step. Use it only if HLDspec implements it, tests it, and the human explicitly approves.
