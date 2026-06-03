# Context Budget Protocol

## Purpose

HLDspec processes large HLDs. Large files are safe for local scripts, but risky for agent/model context.

This protocol separates:

```text
local file processing = safe to read whole files with scripts
agent/model context = must be bounded and explicit
```

## Core rule

Do not load, paste, or rewrite the whole HLD in agent context by default.

Use local tools to inspect files, then bring only bounded evidence into the agent context.

## Safe local tools

These are acceptable because they operate on files locally:

```bash
wc -l HLD.md
grep -nE '^(#|##|###) ' HLD.md
rg -n 'HLD-|REF HLD-|CONFLICTS_WITH|DEPENDS REF' HLD.md
sed -n '120,220p' HLD.md
awk '/^## HLD-/{print NR ":" $0}' HLD.md
```

Safe precise edits are also allowed when explained first:

```bash
sed -i.bak 's/HLD-SPECS: 001/HLD-SPECS: TBD/' HLD.md
```

## Unsafe patterns

Avoid:

```bash
cat huge-HLD.md
```

when output is pasted into the agent/chat.

Avoid:

```text
rewrite the whole HLD in one hidden pass
```

Avoid:

```text
load whole HLD + all specs + all logs into one prompt
```

## HLD conversion budget

When converting raw HLD to HLDspec format:

- preserve `HLD.raw.md`
- edit only the working `HLD.md`
- convert in bounded batches of 3-5 major sections
- for very large candidate sections, inspect internal headings first
- do not split a large section without explaining the reason
- do not invent refs, owners, resources, or spec mappings
- use `HLD-SPECS: TBD` unless certain
- use `HLD-RESOURCES: TBD` unless explicit
- after each batch, report:
  - sections converted
  - metadata chosen
  - refs added
  - uncertain fields
  - diff summary
  - next proposed batch

## Output budget

Prefer summaries over full dumps.

Good:

```text
HLD-002 lines 80-160 converted.
Added role: api.
Added DEPENDS REF HLD-001.
Uncertain: HLD-RESOURCES remains TBD.
Diff summary: metadata inserted; original text preserved.
```

Bad:

```text
<entire 500-line section pasted>
```

## Bounded SpecKit Context Budget

Future SpecKit prework and run-card generation must use a bounded evidence
package:

```text
Spec Build Plan entry
+ full related HLD sections
+ required refs
+ relevant normal refs
+ related API/data/performance/recovery constraints
```

It must not include:

- whole HLD by default
- all existing specs by default
- all logs
- section cards alone as evidence

## Human-in-loop rule

The agent must keep the human able to understand and steer.

Before large or ambiguous work:

```text
What I see
What it means
What I plan to do
Command or edit
Expected result
Human decision needed
```

After each batch:

```text
What happened
Files created or changed
What it means
Next decision
```

Stop for human decision when a step could lock in architecture, ownership, API contracts, data/state, performance/memory, failure/recovery, specs, constitution, downstream artifacts, or implementation.
