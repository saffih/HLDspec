# HLDspec Interview Checkpoint RunSkeptic Review

made by AI

Date: 2026-05-23

## Source of truth

RunSkeptic source read before this patch:

- Repository: `saffih/skeptic`
- File: `skeptic.md`
- Required flow: `GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN`

## Goal

Add a bounded interview layer that records human answers into the controlling checkpoint queue without silently deciding, mutating the source HLD, or invoking SpecKit.

## GATE

DONE is testable:

- valid queue answers are written to JSON
- invalid question IDs are rejected
- invalid options are rejected
- conversion answers regenerate source-HLD update review artifacts
- rerun is optional and requires source HLD path

Wrong-answer cost is bounded:

- only derived workspace artifacts are edited
- source HLD is not modified
- SpecKit is not invoked

Decision: FIX allowed.

## FUNDAMENTAL SCAN

Source of truth:

- active queue JSON owns pending human decisions
- `hldspec_state.json` reports the checkpoint
- source HLD remains authoritative until explicit approval

Boundary:

- `apply_hldspec_queue_answers.py` mutates queue artifacts only
- `hldspec_interview.sh` is the user-facing wrapper
- source-HLD-impact artifacts are review queues, not automatic patches

## MAP

- Charlie Munger (CH): downstream continuation depends on correct queue answers; invalid answers must fail early.
- Occam's Razor (OM): implement queue answer recording before broader interactive UI.
- Richard Feynman (FE): question IDs and allowed options must be visible and enforced.
- Karl Popper (PO): invalid ID/option tests must fail.
- Immanuel Kant (KT): every checkpoint queue should use the same validation pattern.
- Saffi (SH): speed vs safety; safety dominates by refusing unknown IDs/options.

## STABILIZED ISSUES

### Issue 1 - no answer writer

Root cause: checkpoint queues existed but had no simple validated answer-recording command.

Action: add `scripts/apply_hldspec_queue_answers.py`.

Verification: `tests/test_hldspec_interview_answers.py`.

### Issue 2 - user-facing interview missing

Root cause: user had to know which JSON to edit.

Action: add `scripts/hldspec_interview.sh`.

Verification: shell syntax and focused tests.

### Issue 3 - source-HLD-affecting decisions can be lost

Root cause: conversion decisions may affect source-HLD structure and need explicit review queueing.

Action: conversion queue answers trigger decision log and source update queue writers when available.

Verification: focused test asserts source update queue is generated.

## HANDLED

- Validated answer recording.
- Invalid option and ID rejection.
- Source-HLD feedback/update queue regeneration for conversion answers.
- Rerun remains explicit and optional.

## CONFLICTS

### Full interactive terminal UI

- thesis: implement a full prompt-driven UI now
- antithesis: flags are safer and easier to test first
- safe recommendation: keep flag-based interface now; add interactive UI later only if needed
- decision needed: whether interactive UX is worth the added state complexity

### SpecKit proxy execution

- thesis: after answers, run SpecKit automatically
- antithesis: proxy execution still needs one-phase approval and bounded dossier tests
- safe recommendation: defer proxy execution
- decision needed: approve one-phase proxy patch after interview layer stabilizes
