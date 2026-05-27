# HLDspec Gap Handoff Template

A gap handoff is a status and continuation artifact. It is not architecture
truth and does not replace README, the canonical terminology/flow doc, the
SpecKit proxy protocol, or the backlog.

Use this template when handing HLDspec repo work between agents, models, or
sessions.

## Current state

```text
Branch:
HEAD:
Dirty files:
Untracked files:
Current gate/status:
```

## Source of truth files

```text
README.md
docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md
docs/SPECKIT_PROXY_PROTOCOL.md
docs/SPECKIT_SLICE_CONTROL.md
docs/HLDSPEC_ARTIFACT_CONTRACT_STYLE.md
AGENTS.md
```

## What changed

-

## Known gaps

For each gap:

```text
Gap ID:
Status: PASS / ACTION / CONFLICT
Owner:
Affected files:
Why it matters:
Next safe action:
Tests required:
Stop conditions:
Evidence:
```

## What was tested

List exact commands and summarize exact results. Do not say tested if a command
did not run.

```text
Command:
Result:
```

## What was not tested

-

## Next safe patch

```text
Scope:
Expected files:
Focused tests:
Related regression tests:
Full test command:
Generated-output smoke:
Diff/status checks:
```

## Forbidden actions

```text
Do not push unless explicitly instructed.
Do not delete legacy files without a dependency scan.
Do not run raw /speckit.implement.
Do not change product truth silently.
Do not update tests only.
Do not claim tests passed unless exact commands ran.
```

## Validation required

```text
python3 -m unittest discover -s tests_v2 -v
git diff --check
git status --short
```

## Handoff prompt

```text
Continue HLDspec from current local repo. Read this gap handoff first. Treat it
as current status only, not architecture truth. Inspect git status, dirty files,
related code, and related tests before patching. Follow the strict patch
procedure.
```
