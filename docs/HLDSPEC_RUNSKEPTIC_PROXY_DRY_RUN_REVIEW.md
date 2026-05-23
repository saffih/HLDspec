# HLDspec SpecKit Proxy Dry-run RunSkeptic Review

made by AI

Date: 2026-05-23

## Source of truth

RunSkeptic source read before this patch:

- Repository: `saffih/skeptic`
- File: `skeptic.md`
- Required flow: `GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN`

## Goal

Add the bounded SpecKit proxy layer without allowing accidental implementation or unapproved execution.

## GATE

DONE is testable:

- proxy refuses before prework approval
- proxy refuses implementation phase
- proxy accepts exactly one allowed phase after approval
- proxy emits dry-run artifacts only
- approval is recorded explicitly in `speckit_prework_package.json`

Wrong-answer cost is bounded:

- no SpecKit command is invoked
- no source HLD is modified
- no implementation artifacts are created

Decision: FIX allowed.

## FUNDAMENTAL SCAN

Source of truth:

- `speckit_prework_package.json` owns the approval checkpoint
- `hldspec_state.json` owns current stage
- `speckit_proxy_dossier.json` owns feature handoff evidence
- `speckit_proxy_dry_run.json` is a derived guard artifact

Boundary:

- `approve_hldspec_prework.py` records approval only
- `build_speckit_proxy_dry_run.py` builds a dry-run plan only
- `hldspec_speckit_proxy.sh` refuses execution mode

## MAP

- Charlie Munger (CH): downstream proxy execution depends on correct approval state; missing approval must block.
- Occam's Razor (OM): dry-run is the smallest safe proxy layer before real execution.
- Richard Feynman (FE): the artifact must say exactly what would run and what will not run.
- Karl Popper (PO): tests must falsify unapproved proxy and implementation phase.
- Immanuel Kant (KT): every proxy path should use the same approval guard.
- Saffi (SH): speed vs safety; safety dominates until dry-run passes on real HLDs.

## STABILIZED ISSUES

### Issue 1 - proxy could be mistaken as executable

Root cause: dossier said ready after approval but no executable guard existed.

Action: add explicit dry-run builder and wrapper.

Verification: tests assert refusal without approval and readiness after approval.

### Issue 2 - implementation boundary not enforced

Root cause: existing dossier listed implementation as a later SpecKit sequence step.

Action: dry-run refuses `implement` / `implementation` phase.

Verification: test asserts `REFUSED_IMPLEMENT_FORBIDDEN`.

### Issue 3 - approval had no simple explicit recorder

Root cause: prework package had a checkpoint but no small approval command.

Action: add `approve_hldspec_prework.py`.

Verification: test records `APPROVE_PLAN` and then proxy dry-run becomes ready.

## HANDLED

- Bounded dry-run proxy added.
- Explicit prework approval recorder added.
- Implementation remains blocked.
- One-phase-only guard added.
- Tests added for refusal and approved dry-run.

## CONFLICTS

### Real SpecKit invocation

- thesis: invoke SpecKit now after approval
- antithesis: real execution still needs end-to-end validation on a real HLD and tool-specific failure handling
- tradeoff: faster product completeness vs risk of wrong generated artifacts
- safe recommendation: run dry-run on real HLD first; add real one-phase execution only after smoke tests
- decision needed: approve real one-phase execution patch later
