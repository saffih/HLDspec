# HLDspec Question Guide RunSkeptic Review

made by AI

Date: 2026-05-23

## Source of truth

RunSkeptic source read before this patch:

- Repository: `saffih/skeptic`
- File: `skeptic.md`
- Required flow: `GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN`

## Goal

Add a formal read-only checkpoint question guide so a cheap junior guide can help the human answer only real checkpoint questions.

## GATE

DONE is testable:

- state/checkpoint queues can produce `hldspec_question_guide.json/md`
- conversion questions are explained without editing files
- spec-plan questions are explained without editing files
- PMQ/ARQ escalation questions are explained without promotion or SpecKit execution
- status/smoke can point to the guide when a checkpoint blocks progress

Wrong-answer cost is bounded:

- the guide is read-only
- the guide does not answer questions
- the guide does not convert HLDs
- the guide does not invoke SpecKit
- the guide does not promote artifacts

Decision: FIX allowed.

## FUNDAMENTAL SCAN

The current observed blocker is an HLD conversion checkpoint. The product already stops safely, but the human has to manually inspect several files. This is a process gap, not a SpecKit/proxy gap.

Source of truth:

- `hldspec_state.json` identifies the current checkpoint
- the controlling question queue owns the actual questions
- the guide is derived and read-only
- `hldspec_interview.sh` remains the writer for validated answers

Boundary:

- question guide explains
- interview records
- conversion agent converts only after decisions are recorded
- judge/orchestrator remains responsible for flow control

## MAP

- Charlie Munger (CH): unclear checkpoint questions block the whole downstream flow.
- Occam's Razor (OM): a read-only guide is simpler than adding more judge/PM/Architect behavior.
- Richard Feynman (FE): the human needs plain explanations, evidence, options, and risk.
- Karl Popper (PO): tests must prove the guide does not need source-HLD mutation or SpecKit.
- Immanuel Kant (KT): every checkpoint should expose the same explain-before-answer pattern.
- Saffi (SH): speed vs safety; a junior guide improves speed without taking control.

## STABILIZED ISSUES

### Issue 1 - checkpoint questions are discoverable but not guided

Root cause: state points to queues, but no formal guide translates them into human-friendly action.

Action: add `build_hldspec_question_guide.py` and `hldspec_question_guide.sh`.

Verification: conversion/spec-plan/escalation guide tests.

### Issue 2 - smoke stops before later artifacts and leaves unclear next action

Root cause: conversion checkpoint is earlier than PM/Architect/proxy layers.

Action: make smoke/status print or generate the question guide when checkpoint queues exist.

Verification: shell syntax and guide tests.

## HANDLED

- Read-only checkpoint guide added.
- Guide supports conversion, spec-build-plan, and SpecKit escalation queues.
- Interview queue discovery recognizes the escalation queue.
- Smoke/status integration points to the guide.

## CONFLICTS

### Should the guide answer automatically?

Thesis: automatic answers speed conversion.

Antithesis: checkpoint questions are human-owned by design.

Decision: no automatic answering. The guide may recommend only when evidence is explicit, but the human must choose.
