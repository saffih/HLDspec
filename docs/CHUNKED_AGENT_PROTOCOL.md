# Chunked Judge/Subagent Protocol

made by AI

## Purpose

Keep HLDspec work simple, safe, and context-friendly without adding a heavy token-measurement system.

The default protection is:

```text
proper chunks
+ bounded subagent briefs
+ judge/orchestrator review
+ human-in-loop stop points
```

Local scripts may read whole files. Agents and subagents should not hold the whole HLD in model context.

## Core model

```text
Human
-> Judge/orchestrator agent
   -> bounded subagent for chunk A
   -> bounded subagent for chunk B
   -> bounded subagent for chunk C
-> judge reviews subagent outputs
-> judge synthesizes only summaries, risks, decisions, and next steps
-> human decides unresolved issues
```

## Roles

### Human

The human owns unresolved decisions.

### Judge/orchestrator

The judge/orchestrator owns the process and final synthesis.

The judge/orchestrator must:

- understand the overall goal
- choose the next bounded chunk
- brief subagents with exact scope
- enforce context discipline
- review subagent outputs skeptically
- reject or rework incomplete outputs
- maintain the running summary
- escalate unresolved decisions to the human

The judge/orchestrator should not load every chunk in full detail unless needed.

### Subagent

Subagents are bounded workers.

A subagent should receive only:

- the task
- the specific section/chunk or line range
- necessary surrounding context
- allowed commands/files
- forbidden actions
- stop conditions
- required output format

Subagents do not own final decisions.

## Chunking rules

Use these simple defaults:

```text
Normal chunk: 1 major HLD section
Small-section batch: 3-5 major sections when sections are small enough
Large section: process alone
Very large section: inspect internal headings first before editing/splitting
```

Do not rewrite the whole HLD in one hidden pass.

Do not pass the whole HLD to a subagent by default.

Use local tools for bounded extraction:

```bash
grep -nE '^(#|##|###) ' HLD.md
sed -n '120,220p' HLD.md
rg -n 'REF HLD-|DEPENDS REF|CONFLICTS_WITH|HLD-SPECS|HLD-ROLE' HLD.md
wc -l HLD.md
```

## Required subagent brief

Every subagent brief must include:

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

## Required subagent output

Every subagent must report:

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

## HLD conversion workflow

When converting raw HLD to HLDspec format:

1. Preserve `HLD.raw.md`.
2. Edit only the working `HLD.md`.
3. Work by major section chunks.
4. Use `HLD-SPECS: TBD` unless mapping is certain.
5. Use `HLD-RESOURCES: TBD` unless resources are explicit.
6. Add refs only when supported by the text.
7. After each chunk, report:
   - sections converted
   - metadata chosen
   - refs added
   - uncertain fields
   - diff summary
   - next proposed chunk

## Running summary

The judge/orchestrator should maintain a compact running summary:

```text
Sections completed:
Open uncertainties:
Conflicts:
Decisions needed:
Potential splits:
Next chunk:
```

This protects the judge from accumulating the full HLD in context.

## Stop for human decision

Stop and ask the human before:

- accepting `DECOMPOSE`
- accepting `CONFLICT`
- accepting `SPLIT_PLANNED_SPEC`
- accepting `RESOLVE_CONFLICT`
- splitting major HLD sections when interpretation is involved
- creating or modifying specs
- creating or modifying target constitution
- creating downstream artifacts
- modifying implementation files
- choosing architecture, ownership, API, data/state, performance/memory, or failure/recovery behavior

## Downstream analysis as a bounded chunk task

`downstream_analysis.md` is not a first-run artifact. It is produced only after the relevant upstream scope is accepted.

Treat downstream analysis as a bounded delegated task:

```text
Judge/orchestrator
-> chooses accepted scope
-> briefs downstream-analysis subagent
-> limits context
-> reviews output
-> escalates unresolved decisions

Downstream-analysis subagent
-> analyzes only the assigned accepted scope
-> reports evidence, gaps, risks, uncertainty, and human decisions needed
```

Do not ask a downstream-analysis subagent to analyze the full HLD by default.

Do not produce downstream artifacts from raw-HLD assumptions.


## Do not over-engineer

Do not add numeric token measurement unless repeated failures show chunking is insufficient.

The simple default is:

```text
one chunk at a time
one subagent task at a time
judge reviews summaries
human decides unresolved issues
```
