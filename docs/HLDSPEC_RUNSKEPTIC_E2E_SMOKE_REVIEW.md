# HLDspec End-to-End Smoke RunSkeptic Review

made by AI

Date: 2026-05-23

## Source of truth

RunSkeptic source read before this patch:

- Repository: `saffih/skeptic`
- File: `skeptic.md`
- Required flow: `GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN`

## Goal

Add a repeatable real-HLD smoke harness that verifies the product foundation without invoking real SpecKit or implementation.

## GATE

DONE is testable:

- smoke runs prework and status
- smoke runs alignment review
- smoke can optionally approve only the guarded dry-run
- smoke runs proxy dry-run
- readiness report is generated
- source HLD hash is checked before and after

Wrong-answer cost is bounded:

- source HLD is not modified
- real SpecKit is not invoked
- implementation remains blocked

Decision: FIX allowed.

## FUNDAMENTAL SCAN

Source of truth:

- source HLD remains authoritative
- workspace artifacts are derived
- readiness review summarizes current product state

Boundary:

- `hldspec_smoke.sh` orchestrates existing product wrappers
- `run_hldspec_readiness_review.py` reports readiness only
- no real SpecKit execution is introduced

## MAP

- Charlie Munger (CH): if source HLD mutates during smoke, downstream evidence is invalid.
- Occam's Razor (OM): one smoke command is simpler than requiring the user to remember the sequence.
- Richard Feynman (FE): readiness report must say exactly what passed, what is missing, and what remains deferred.
- Karl Popper (PO): missing artifacts and source mutation must be detectable.
- Immanuel Kant (KT): every real-HLD validation should use the same smoke path.
- Saffi (SH): product speed vs safety; smoke harness gives speed without crossing into execution risk.

## STABILIZED ISSUES

### Issue 1 - product readiness requires too many manual commands

Root cause: prework/status/approval/dry-run/readiness were separate commands.

Action: add `scripts/hldspec_smoke.sh`.

Verification: focused smoke/readiness tests.

### Issue 2 - readiness was implicit

Root cause: no single artifact summarized whether the product foundation is ready or blocked.

Action: add `scripts/run_hldspec_readiness_review.py`.

Verification: tests for missing foundation artifacts and dry-run-ready state.

### Issue 3 - source mutation could go unnoticed

Root cause: smoke had no before/after source hash check.

Action: smoke records and verifies source SHA-256.

Verification: smoke script logic and readiness review source hash path.

## HANDLED

- End-to-end smoke harness added.
- Readiness review added.
- Source-HLD hash check added.
- Real SpecKit execution remains deferred.

## CONFLICTS

### Real one-phase SpecKit execution

- thesis: add real execution after smoke
- antithesis: real tool invocation requires tool-specific failure handling and rollback expectations
- safe recommendation: run smoke on real HLD first, inspect readiness report, then decide
- decision needed: approve or defer real one-phase execution patch
