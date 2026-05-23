# HLDspec Weak-Agent Bootstrap RunSkeptic Review

made by AI

Date: 2026-05-23

## Goal

Fix the observed failure where a cheap/small fresh agent received the minimal trigger but restarted the raw first-run path instead of reading the generated context and continuing from `CONVERSION_READY_TO_APPLY`.

## GATE

DONE is testable:

- root `AGENTS.md` tells agents how to expand `HLDspec ...`
- generated context forbids web/memory search before context
- generated context does not advertise `first_run_readonly.sh` as an allowed current command at `CONVERSION_READY_TO_APPLY`
- generated context provides first-run command only as an after-conversion command
- tests prove conversion-ready behavior

Decision: FIX allowed.

## FUNDAMENTAL SCAN

The minimal trigger is correct for the user, but weak agents need an explicit bootstrap rule. The bootstrap must live in repo-level instructions and generated context, not in a long user prompt.

## MAP

- Munger: weak agents follow visible commands; listing the wrong command at the current stage causes wrong behavior.
- Occam: keep the user trigger small and move complexity into bootstrap docs/context.
- Feynman: at `CONVERSION_READY_TO_APPLY`, the instruction must say simply: convert first, do not rerun.
- Popper: tests must verify no current allowed command includes `first_run_readonly` at conversion-ready stage.
- Kant: every fresh agent must follow the same bootstrap path.
- Saffi: low-cost agents need strict, small, deterministic instructions.

## DECISION

HANDLED.

No real SpecKit execution added.
