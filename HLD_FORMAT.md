# HLD Format for HLDspec

This document defines a lightweight, grepable HLD input format for `hld_spec_sync.py` and `hld_spec_downstream.py`.

Goal: keep one human-editable `HLD.md` while making each section easy to grep, map, validate, chunk, and process without loading the whole HLD into one model context.

## Core rule

`HLD.md` is the canonical source of truth.

Generated files under `.specify/sync/` are derived artifacts and may be regenerated.

Prefer one canonical HLD with stable section IDs and grepable metadata. Do not manually maintain many HLD source files unless the project explicitly chooses that.

## Required section shape

Each major HLD section uses a stable heading and a small metadata block immediately below it.

```md
## HLD-003 - Sync Engine

HLD-ID: HLD-003
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: 001,002
HLD-RESOURCES: hld_spec_sync.py,.specify/memory/constitution.md,specs/*/spec.md
HLD-VERIFY: related specs preserve HLD anchors; feature graph includes dependencies

### Purpose
...
```

## Required metadata fields

| Field | Required | Meaning |
|---|---:|---|
| `HLD-ID` | yes | Stable section ID. Must match the heading ID. |
| `HLD-ROLE` | yes | Section role, such as purpose, governance, architecture, processing, api, ui, operations, testing, risk. |
| `HLD-STATUS` | yes | `active`, `planned`, `deprecated`, or `needs-review`. |
| `HLD-RISK` | yes | `LOW`, `MEDIUM`, or `HIGH`. |
| `HLD-SPECS` | yes | Related Spec Kit spec IDs, `constitution`, or `TBD`. |
| `HLD-RESOURCES` | yes | Related files, directories, generated artifacts, APIs, prompts, or configs. |
| `HLD-VERIFY` | yes for HIGH risk | How this section should be checked. |

Optional fields: `HLD-OWNER`, `HLD-NOTES`, `HLD-OUTPUTS`, `HLD-INPUTS`.

## Section references

Use inline references inside normal HLD prose.

```md
This flow uses the source-of-truth rules in REF HLD-002.
This section DEPENDS REF HLD-002 because source-of-truth rules decide what may be generated.
This rollout is BLOCKED_BY REF HLD-009 until the owner approves the migration path.
This approach CONFLICTS_WITH REF HLD-011 because both define different rollback authority.
```

## Reference semantics

| Pattern | Meaning | Load behavior |
|---|---|---|
| `REF HLD-xxx` | Related context | Load when relevant or when budget allows. |
| `DEPENDS REF HLD-xxx` | Required context | Always load. |
| `BLOCKED_BY REF HLD-xxx` | Blocking dependency or decision | Always load and report as blocker. |
| `CONFLICTS_WITH REF HLD-xxx` | Known conflict | Always load and preserve as conflict unless resolved by human decision. |

## Grep examples

```bash
grep -n "^## HLD-" HLD.md
grep -n "^HLD-ID:" HLD.md
grep -n "^HLD-ROLE:" HLD.md
grep -n "^HLD-RISK: HIGH" HLD.md
grep -n "REF HLD-" HLD.md
grep -n "DEPENDS REF HLD-" HLD.md
grep -n "BLOCKED_BY REF HLD-" HLD.md
grep -n "CONFLICTS_WITH REF HLD-" HLD.md
```

## Map generation behavior

A tool may build a temporary or generated map by reading:

1. `## HLD-xxx - Title` headings
2. `HLD-*:` metadata lines
3. inline `REF HLD-xxx` references

Map tooling should ignore HLD-looking headings, metadata, and references inside fenced code blocks. Manual `grep` results are candidates and may include examples if the HLD itself contains fenced Markdown snippets.

Generated outputs may include:

```text
.specify/sync/hld_ref_map.json
.specify/sync/hld_index.md
.specify/sync/hld_sections/<section-id>.md
.specify/sync/chunk_plan.json
```

These files are derived from `HLD.md` and can be regenerated.

## Start and end of sections

A section starts at:

```md
## HLD-xxx - Title
```

A section ends immediately before the next:

```md
## HLD-yyy - Title
```

The generated map should store calculated line ranges.

## Validation rules

The HLD format is valid only if:

- Every major section heading has a stable `HLD-xxx` ID.
- Every section has exactly one `HLD-ID` line.
- Heading ID and `HLD-ID` value match.
- No duplicate `HLD-ID` values exist.
- Every `REF HLD-xxx` points to an existing HLD section or is explicitly marked `TBD` nearby.
- Every `DEPENDS REF`, `BLOCKED_BY REF`, and `CONFLICTS_WITH REF` is included in the generated map.
- Every high-risk section has `HLD-VERIFY`.
- Every section has `HLD-SPECS` with real IDs, `constitution`, or `TBD`.
- Every section has `HLD-RESOURCES`, even if the value is `TBD`.
- Cycles are detected and reported, not followed forever.

## Context loading rule

When processing one section, load:

1. the target section
2. sections referenced by `DEPENDS REF`
3. sections referenced by `BLOCKED_BY REF`
4. sections referenced by `CONFLICTS_WITH REF`
5. normal `REF` sections when relevant and within budget
6. related specs from `HLD-SPECS`
7. related files/artifacts from `HLD-RESOURCES`
8. only the relevant slice of generated sync metadata

Default reference depth: 1. High-risk sections may use depth 2, but skipped references must be reported when prompt budget is exceeded.

## Example section

```md
## HLD-007 - Chunked Processing

HLD-ID: HLD-007
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: TBD
HLD-RESOURCES: hld_spec_sync.py,hld_spec_downstream.py,.specify/sync/hld_ref_map.json
HLD-VERIFY: large HLD can be processed without loading full document; section refs are preserved; duplicate specs are not created

### Purpose

Define how large HLD files are processed without putting the full document and all specs into one model context.

This section DEPENDS REF HLD-002 because source-of-truth rules define which generated artifacts may be updated.

This section REF HLD-003 because sync processing uses the same write-target protections.

This section REF HLD-006 for rollback behavior.
```

This is an excerpt. A complete HLD must define referenced sections or mark unknown references as `TBD` nearby.

## Practical editing rules

When adding a new major section:

1. Add a new `## HLD-xxx - Title` heading.
2. Add the required `HLD-*` metadata block.
3. Use inline `REF HLD-xxx` references in prose.
4. Do not renumber existing section IDs.
5. Mark unknown specs/resources as `TBD` rather than inventing them.

When changing an existing section:

1. Keep the same `HLD-ID` unless the section meaning truly changed.
2. Update `HLD-SPECS`, `HLD-RESOURCES`, and references if the change affects them.
3. Add `CONFLICTS_WITH REF HLD-xxx` when a real unresolved conflict exists.
4. When map-validator tooling exists, run it before map-aware sync or downstream processing; until then, manually check headings, metadata, and references.
