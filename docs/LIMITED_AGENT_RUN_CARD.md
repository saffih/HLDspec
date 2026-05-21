# Limited Agent Run Card

made by AI

Use this when the agent has limited context/capacity.

Read this short card before longer docs.

## Mission

Use `~/HLDspec` to process a project HLD while keeping the human able to understand and steer.

## Role

You are the **judge/orchestrator**.

You may use subagents, but only as bounded workers on specific chunks.

You remain responsible for:

- briefing subagents
- limiting their context
- reviewing their output
- rejecting incomplete work
- keeping a compact running summary
- escalating unresolved decisions to the human

Subagents do not own final decisions.

The human owns unresolved decisions.

## Hard rules

1. Do not load or paste the whole HLD into model context.
2. Use local tools for bounded inspection: `grep`, `rg`, `sed -n`, `awk`, `wc`, `head`, `tail`.
3. Preserve the original HLD. Edit only the working copy inside `$WORK`.
4. Keep the human in the loop.
5. Do not silently continue through `DECOMPOSE`, `CONFLICT`, `SPLIT_PLANNED_SPEC`, or `RESOLVE_CONFLICT`.
6. Do not create or modify specs, target constitution, downstream artifacts, or implementation files without explicit human approval.
7. Do not invent architecture decisions, refs, owners, resources, or spec IDs.

## First command

From the project repo:

```bash
HLD="./Simulator-System-HLD.md"
WORK="$PWD/.hldspec-first-run"
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

Then convert `"$WORK/HLD.md"` in chunks.

### Any other exit code

Stop and report the error. Do not continue.

## Chunking rule

Use simple chunks:

```text
Normal chunk: 1 major HLD section
Small-section batch: 3-5 major sections when sections are small enough
Large section: process alone
Very large section: inspect internal headings first
```

After each chunk, report:

```text
Sections converted:
Metadata chosen:
Refs added:
Uncertain fields:
Files changed:
Diff summary:
Next proposed chunk:
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

## Subagent brief template

Use this for every subagent:

```text
Role:
Task:
Chunk:
Relevant context:
Allowed files/commands:
Forbidden actions:
Context rule:
Stop conditions:
Required output:
Evidence required:
```

## Subagent output template

Require:

```text
What I inspected:
What I changed, if anything:
What I found:
Evidence:
Uncertainty:
Risks:
Recommended action:
Files changed:
Human decision needed:
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

## Stop for human decision

Stop and ask the human before:

- accepting `DECOMPOSE`
- accepting `CONFLICT`
- accepting `SPLIT_PLANNED_SPEC`
- accepting `RESOLVE_CONFLICT`
- splitting major HLD sections when interpretation is involved
- choosing architecture, source-of-truth, ownership, API, data/state, performance/memory, or failure/recovery behavior
- creating or modifying specs
- creating or modifying target constitution
- creating downstream artifacts
- modifying implementation files


## Minimal success path

```text
1. Run first_run_readonly.sh.
2. If raw, convert HLD.md in bounded chunks.
3. Rerun first_run_readonly.sh on the converted HLD.md.
4. Summarize spec_build_plan_review.md.
5. Stop if blocked; ask the human.
```

## Do not proceed to target-spec generation

Target-spec generation is not the default next step. Use it only if HLDspec implements it, tests it, and the human explicitly approves.
