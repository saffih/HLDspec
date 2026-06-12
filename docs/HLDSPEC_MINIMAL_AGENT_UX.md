# HLDspec Minimal Agent UX

## Purpose

Let a user start HLDspec with one short instruction instead of a long prompt.

The agent must expand the short request into the public HLDspec facade and report only decision-oriented output back to the user.

## Minimal request shapes

Accepted user requests include:

```text
HLDspec help
HLDspec help status
HLDspec help what next
HLDspec HLD: /path/to/HLD.md create /path/to/target
HLDspec create /path/to/target from /path/to/HLD.md
HLDspec HLD: /path/to/HLD.md target: /path/to/target runtime: claude
```

Concrete example:

```text
HLDspec HLD: /Users/saffi/code/flow/flow-hld.md create /Users/saffi/code/flowHld runtime claude
```

## Extracted fields

| Field | Required | Default | Notes |
|---|---|---|---|
| source_hld | yes | none | Existing source HLD path. Treat as read-only evidence. |
| target_workspace | yes | none | HLDspec target workspace to create/adopt/resume. |
| mode | no | auto | If the user says `create`, use create unless the target already has state and safety requires adopt/resume. |
| runtime | no | claude | One of `claude`, `codex`, or `devin`. |
| comment | no | compact generated summary | Include any extra user intent, constraints, or runtime notes. |

## Runtime rule

Supported runtime values:

- claude
- codex
- devin

Default runtime: claude.

The first implementation target is Claude. Codex and Devin remain supported configuration values for future runtime adapters unless the current product flow already supports them.

## Agent behavior

When a minimal request is detected, the agent must:

1. Extract source HLD, target workspace, mode, runtime, and comment.
2. Use only the public HLDspec facade for normal product flow: `start`, `status`, `review`, `doctor`, and later `continue` when safe.
3. Avoid exposing low-level implementation scripts to the user unless debugging a failure.
4. Keep the source HLD read-only.
5. Write generated state only under the target workspace.
6. Stop on ACTION or CONFLICT.
7. When the user asks for help, explain the safest status/next-action path first:
   `HLDspec status target: <path>`, then `doctor`, then `operator-state` when readiness/build-loop safety is the question.
8. Return a short status with:
   - target
   - mode
   - runtime
   - blockers
   - next safe action

## Help behavior

Help is part of the public UX. A user should be able to ask:

```text
HLDspec help
HLDspec help status
HLDspec help what next
HLDspec help target prompts
```

The default answer must tell the user that `status` is the safest first
question when they are unsure, because it reports current state, blockers, open
questions, evidence, and the next safe action without advancing the workflow.

Every topic help response should use the bounded shape:

```text
Purpose
Does
Stops at
Will not
Example
```

## Flow example expansion

For:

```text
HLDspec HLD: /Users/saffi/code/flow/flow-hld.md create /Users/saffi/code/flowHld runtime claude
```

The agent should prepare an HLDspec session with:

```text
source: /Users/saffi/code/flow/flow-hld.md
target: /Users/saffi/code/flowHld
mode: create
runtime: claude
comment: Create Flow product target from flow-hld.md. Runtime config supports claude, codex, and devin; default and first target is claude; codex/devin are future runtimes; core remains runtime-agnostic and provider behavior belongs in adapters/config.
```

Then the agent reports the resulting status, blockers, and next safe action.

## Non-goals

- Do not require the user to write a long setup prompt.
- Do not require the user to know low-level script names.
- Do not implement Codex or Devin runtime behavior just because they appear in the config enum.
- Do not claim product readiness without tests and RunSkeptic evidence.
