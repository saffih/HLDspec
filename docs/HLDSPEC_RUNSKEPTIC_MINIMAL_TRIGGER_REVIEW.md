# HLDspec Minimal Trigger RunSkeptic Review

made by AI

Date: 2026-05-23

## Goal

Fix the UX gap where the user was still asked to paste a long generated prompt.

Desired human-facing trigger:

```text
HLDspec /absolute/path/to/HLD.md
```

## GATE

DONE is testable:

- start script still generates full internal context
- start script prints a short minimal trigger by default
- full context is available only in generated files or with explicit `--print-context`
- tests prove the minimal trigger file exists and does not contain the full rules
- no real SpecKit execution is added

Decision: FIX allowed.

## FUNDAMENTAL SCAN

The CLI is internal machinery. The product surface is the agent trigger.

The prior implementation generated correct context but pushed too much text into the human workflow. That violates the product goal.

## MAP

- Munger: asking the human to paste long rules creates user error.
- Occam: one trigger is simpler and sufficient.
- Feynman: generated context should still explain the state, but not be the user's prompt.
- Popper: test the minimal trigger file and default wrapper output behavior.
- Kant: every HLD should start the same way.
- Saffi: speed requires a tiny trigger; safety remains in context files and gates.

## DECISION

HANDLED.

The long context remains available for the agent/tooling. The default human-facing handoff is now the minimal trigger.
