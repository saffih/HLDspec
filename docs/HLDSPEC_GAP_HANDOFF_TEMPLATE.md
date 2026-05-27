# HLDspec Gap Handoff

Use this template when handing HLDspec repo work to another agent, model, or session.

This document is a status and continuation artifact. It is not architecture truth. If it conflicts with `README.md`, `docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md`, or `docs/SPECKIT_PROXY_PROTOCOL.md`, the canonical docs win.

## 1. Status

Status: PASS / ACTION / CONFLICT

One-line summary:

```text
...
```

## 2. Current source of truth

Read these first:

```text
README.md
docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md
docs/SPECKIT_PROXY_PROTOCOL.md
docs/SPECKIT_SLICE_CONTROL.md
AGENTS.md
```

## 3. Current repo state

```text
branch:
HEAD:
git status --short:
dirty files:
untracked files:
last known good commit:
```

## 4. What changed

```text
- ...
```

## 5. Known gaps

For each gap:

```text
ID:
Severity: P0 / P1 / P2
Status: ACTION / CONFLICT / DEFERRED
Owner:
Affected files:
Why it matters:
Next safe action:
Required tests:
```

## 6. Slice-control state

```text
README explains concept: yes/no
Slice-control technical doc present: yes/no
SpecKit proxy protocol updated: yes/no
Generated policy implemented: yes/no
Focused tests added: yes/no
Full tests_v2 passing: yes/no/unknown
```

## 7. Human decisions required

Only list decisions that cannot be answered from existing source truth.

```text
- ...
```

## 8. Next safe patch

```text
Patch goal:
Expected files:
Focused tests:
Related regression tests:
Generated-output smoke:
Full-suite command:
Stop conditions:
```

## 9. Forbidden actions

```text
- Do not push unless explicitly instructed.
- Do not delete or move legacy files without dependency search.
- Do not run raw /speckit.implement unless full implementation is explicitly approved.
- Do not update tests only.
- Do not claim tested unless exact commands ran.
```

## 10. Validation evidence

Commands actually run:

```text
...
```

Output summary:

```text
...
```

## 11. Copy-ready handoff prompt

```text
Continue HLDspec from current local repo.
Local repo is authoritative. GitHub is only the sync target.
Do not push unless explicitly instructed.
Start with git status --short and git log --oneline -8.
Read README.md, docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md, docs/SPECKIT_PROXY_PROTOCOL.md, docs/SPECKIT_SLICE_CONTROL.md, and AGENTS.md.
Then follow the next safe patch section in this Gap Handoff.
```
