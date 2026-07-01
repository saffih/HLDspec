# Minimal HLD Loop

This document describes convenience aliases for Codex/Claude sessions.

The canonical public HLDspec UX remains documented in
`docs/HLDSPEC_MINIMAL_AGENT_UX.md`.

The canonical system model remains documented in
`docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md`.

On conflict, those canonical docs win.

These aliases are agent instructions for Codex/Claude sessions in the HLDspec
repo. They are not CLI commands, shell commands, runtime APIs, or automation.

## Workflow

1. User opens Codex/Claude in the HLDspec repo.
2. User may use the convenience alias: `HLD draft target <target-repo> from <goal/context>`.
3. Agent drafts a brownfield HLD from target state and goals.
4. Human approves writing the HLD into the control plan.
5. Control plan stores TargetBinding and ToolchainBinding. Default toolchain: `speckit`.
6. User may use the convenience alias: `HLD inspect plan <control-plan>`.
7. Agent reports the next human-approved action.
8. User may use the convenience alias: `HLD backlog plan <control-plan>`.
9. Agent proposes a dependency-aware backlog.
10. Human approves the backlog.
11. User may use the convenience alias: `HLD select plan <control-plan> spec <SPEC-ID>`.
12. User may use the convenience alias: `HLD speckit plan <control-plan>`.
13. Agent outputs exact target-side instructions:
    - `cd <target-repo>`
    - open an agent with the SpecKit skill/toolchain
    - paste the generated prompt
14. Target-side agent creates SpecKit artifacts for the selected spec only.
15. User returns to the HLDspec repo.
16. User may use the convenience alias: `HLD inspect plan <control-plan>`.
17. Agent checks completion and next READY specs.
18. Human selects the next READY spec.
19. Repeat.

## Boundaries

HLDspec controls planning. The control plan is the source of truth. The target
repo is the implementation subject. SpecKit runs in the target repo. The human
carries bounded handoff between HLDspec and the target agent.

Human approval is required before HLD writes, backlog writes, spec selection,
handoff, or implementation.

## Forbidden By Default

- No automatic active-spec selection.
- No automatic next-spec selection.
- No implementation during inspect/draft/backlog.
- No target repo mutation during HLD draft.
- No control-plan mutation without approval.
- No broad repo scan when bounded inspection is enough.
- No creating SpecKit artifacts for more than one selected spec.
- No running SpecKit inside HLDspec.

## Handoff Prompt Template

```text
GO TO TARGET REPO:

cd <target-repo>

OPEN AGENT:

Open an agent with the <toolchain> target skill available.

PASTE THIS:

Use <toolchain>.

Create target-side spec artifacts for the selected active spec only.

Selected spec: <SPEC-ID>
Control plan: <control-plan>
Target repo: <target-repo>

Authority:
- approved HLD from the control plan
- selected active spec
- dependency state from the control plan
- current target repo state
- do-not-touch areas

Rules:
- do not implement code unless explicitly approved
- do not create artifacts for other backlog specs
- do not mutate the HLDspec control plan
- do not select the next spec
- stop if the selected spec is blocked, ambiguous, or conflicts with the HLD

Return:
- files created
- target-side artifacts path
- assumptions
- gaps
- next human action
```
