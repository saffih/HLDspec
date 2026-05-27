# Agent Artifact Hygiene

## Purpose

Agents sometimes create notes, reviews, scratch reports, prompts, or diagnostic
documents outside the normal HLDspec product flow. Those artifacts must not
clutter the repo root, masquerade as canonical docs, or become hard to clean up.

This policy defines where ad hoc agent-created artifacts go and how they should
be named.

## Core rule

If an artifact is not part of a known product flow, put it in a bounded ad hoc
location with a date, owner/source, and status.

Do not add one-off files to the repo root.

## Artifact classes

### Canonical product docs

Use for durable, actively maintained design and product references.

Location:

```text
docs/
```

Rules:

- Add the doc to `docs/DOCS_INDEX.md`.
- State whether it is authoritative, supporting, or a policy.
- Keep it maintained; do not use canonical docs for one-time run notes.

### Historical reviews and one-time design records

Use for point-in-time RunSkeptic reviews, design reviews, conflict records, and
decision snapshots that should be preserved but not maintained as active docs.

Location:

```text
docs/archive/
```

Name:

```text
YYYY-MM-DD_<short-topic>_<kind>.md
```

Existing uppercase legacy names are allowed, but new files should prefer the
dated form.

Examples:

```text
docs/archive/2026-05-27_target-workflow-change-ledger_review.md
docs/archive/2026-05-27_p0-session-control_runskeptic.md
```

Required header:

```text
# <Title>

Status: archive | superseded | evidence | conflict-record
Date: YYYY-MM-DD
Scope: <repo, target, or feature>
Owner: agent | human | RunSkeptic | consultant
Canonical references: <links>
```

### Runtime development handoff

Use for temporary handoff from one model/agent/session to another during HLDspec
repo development.

Location:

```text
.hldspec-dev/handoff/
```

Rules:

- `.hldspec-dev/` is runtime state and should stay gitignored.
- Do not commit generated handoff packets unless explicitly requested.
- Durable decisions from a handoff belong in tracked docs or backlog, not hidden
  runtime state.

### Target product runtime artifacts

Use for target-specific HLDspec state and generated artifacts.

Location:

```text
target/.hldspec/
target/.hldspec/source_package/
target/.specify/
```

Rules:

- Follow `TargetWorkspaceAdapter` paths.
- Do not write target product artifacts into the HLDspec repo.
- Do not write HLDspec-authored canonical artifacts into `.specify/`; only
  generated mirrors belong there.

### Ad hoc scratch artifacts

Use when an artifact is purely temporary and not worth preserving.

Preferred location:

```text
/private/tmp/hldspec-<slug>/
```

Rules:

- Do not commit scratch artifacts.
- If scratch output becomes evidence, move the relevant summary into
  `docs/archive/` with a dated filename.

## Cleanup metadata

Every preserved ad hoc artifact should answer:

- Why does this file exist?
- Is it active, archived, superseded, or temporary?
- What canonical doc or code path does it support?
- Can it be deleted after a date, commit, or decision?

Use this footer when cleanup matters:

```text
Cleanup: keep until <condition>; then archive/delete.
```

## Agent checklist

Before creating a document, an agent should decide:

1. Is this canonical? If yes, put it in `docs/` and update `DOCS_INDEX.md`.
2. Is this a point-in-time record? If yes, put it in `docs/archive/` with a date.
3. Is this runtime handoff? If yes, put it under `.hldspec-dev/`.
4. Is this target product state? If yes, put it under the target workspace.
5. Is this scratch? If yes, use `/private/tmp/` and do not commit it.

If none applies, ask before writing.
