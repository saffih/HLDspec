# HLD Generation Prompt for HLDspec

Use this prompt when asking an agent to create or improve an HLD that will later be processed by HLDspec.

## Role

You create or improve a High-Level Design document that remains human-readable and can be processed by HLDspec tooling.

The HLD must use stable `HLD-xxx` section headings, grepable `HLD-*` metadata lines, and inline `REF HLD-xxx` section references.

## Source-of-truth rule

The output HLD is the canonical source of truth.

Generated files such as `.specify/sync/hld_ref_map.json`, `.specify/sync/hld_index.md`, `.specify/sync/hld_sections/*.md`, and `.specify/sync/chunk_plan.json` are derived from the HLD and may be regenerated.

## Required HLD section format

Every major section must use:

```md
## HLD-xxx - Section Title

HLD-ID: HLD-xxx
HLD-ROLE: <role>
HLD-STATUS: active|planned|deprecated|needs-review
HLD-RISK: LOW|MEDIUM|HIGH
HLD-SPECS: <spec ids, constitution, or TBD>
HLD-RESOURCES: <related files/artifacts/resources or TBD>
HLD-VERIFY: <verification rule, required for HIGH risk>

### Purpose
...

### Responsibilities
...

### Inputs
...

### Outputs
...

### Failure Modes
...

### Open Questions
...
```

## Reference rules

Use inline references in the prose:

- `REF HLD-xxx` for related context
- `DEPENDS REF HLD-xxx` for mandatory context
- `BLOCKED_BY REF HLD-xxx` for blocking sequence or approval dependency
- `CONFLICTS_WITH REF HLD-xxx` for unresolved design conflict

Do not invent references. Use `TBD` when unknown.

## Required behavior

1. Preserve existing `HLD-ID` values unless the user explicitly asks to reorganize IDs.
2. Do not renumber existing sections.
3. Add new IDs only for new major sections.
4. Every high-risk section must include `HLD-VERIFY`.
5. Every section must list `HLD-SPECS` and `HLD-RESOURCES`.
6. Every dependency or cross-section relationship must be written as `REF HLD-xxx` in normal prose.
7. Mark unknown specs, resources, or owners as `TBD`.
8. If source of truth, approval, risk, or contract is unclear, mark it as `TBD` or `CONFLICT`; do not silently resolve it.
9. Mark unresolved design conflicts with `CONFLICTS_WITH REF HLD-xxx` in prose, or with `CONFLICT` in open questions and self-check notes.
10. Keep the HLD readable as a normal Markdown document.
11. Avoid creating many source HLD files unless explicitly requested.
12. Treat generated section/chunk files as derived artifacts, not as canonical HLD source.

## HLD skeleton

```md
# High-Level Design: <Project Name>

## HLD-001 - Executive Summary

HLD-ID: HLD-001
HLD-ROLE: purpose
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: summary matches goals, non-goals, and architecture sections

### Purpose

### Scope

### Non-Goals

## HLD-002 - Source of Truth and Governance

HLD-ID: HLD-002
HLD-ROLE: governance
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: .specify/memory/constitution.md,.specify/sync/spec_index.json
HLD-VERIFY: generated specs preserve HLD anchors and do not contradict constitution

### Purpose

### Source-of-Truth Rules

### Human Decisions

### Verification

## HLD-003 - Architecture Overview

HLD-ID: HLD-003
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: architecture dependencies use concrete section references

### Purpose

This section DEPENDS REF HLD-002 because governance defines what can be generated or changed.

### Components

### Main Flows

### Interfaces

### Risks
```

## Output requirement

Return a complete Markdown HLD.

Do not return only an outline unless the user asked for an outline.

End with:

```md
## HLD Format Self-Check

| Check | Status |
|---|---|
| Every major section has `## HLD-xxx - Title` | PASS/FAIL |
| Every section has `HLD-ID` | PASS/FAIL |
| Heading ID matches `HLD-ID` | PASS/FAIL |
| No duplicate `HLD-ID` values exist | PASS/FAIL |
| Every high-risk section has `HLD-VERIFY` | PASS/FAIL |
| Every section has `HLD-SPECS` | PASS/FAIL |
| Every section has `HLD-RESOURCES` | PASS/FAIL |
| Section references use `REF HLD-xxx` syntax | PASS/FAIL |
| Unknown ownership/source-of-truth/spec mappings are marked `TBD` or `CONFLICT` | PASS/FAIL |
| Unresolved design conflicts are marked with `CONFLICTS_WITH REF HLD-xxx` or `CONFLICT` | PASS/FAIL |
```
