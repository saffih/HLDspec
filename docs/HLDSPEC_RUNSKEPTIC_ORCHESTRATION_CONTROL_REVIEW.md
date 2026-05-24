# HLDspec Orchestration Control RunSkeptic Review

Date: 2026-05-23

## Source of truth

RunSkeptic source read before this patch:

- Repository: `saffih/skeptic`
- File: `skeptic.md`
- Required flow: `GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN`

## Goal

Add judge-owned promotion gates and senior-to-junior delegation contracts before triggering real agents or real SpecKit execution.

## GATE

DONE is testable:

- artifacts exist as `PROPOSED` by default
- Product Manager pack existence does not equal acceptance
- Architect pack existence does not equal acceptance
- answer pack cannot be accepted until Product Manager and Architect packs are accepted
- proxy dry-run refuses unpromoted answer pack
- junior task packets include cost tier, limited context, forbidden actions, and strict output schemas

Wrong-answer cost is bounded:

- only derived workspace artifacts are written
- source HLD is not modified
- real agents are not triggered
- real SpecKit is not invoked
- implementation remains blocked

Decision: FIX allowed.

## FUNDAMENTAL SCAN

Source of truth:

- promotion ledger owns promotion decisions
- orchestration state reports allowed/blocked actions
- specialist artifacts remain proposed until promoted
- junior task packets are work instructions, not decisions

Boundaries:

- judge owns global promotion
- senior roles synthesize domain outputs
- junior agents extract/draft only
- proxy consumes promoted evidence only

## MAP

- Charlie Munger (CH): downstream SpecKit behavior depends on accepted evidence; proposed artifacts must not control.
- Occam's Razor (OM): add a simple ledger and state builder before real agent execution.
- Richard Feynman (FE): state must show what exists, what is accepted, and what blocks progress.
- Karl Popper (PO): tests must falsify artifact-exists-implies-approved.
- Immanuel Kant (KT): every artifact should use the same promotion pattern.
- Saffi (SH): speed vs safety; junior agents reduce cost while judge promotion preserves control.

## STABILIZED ISSUES

### Issue 1 - artifact existence can be confused with approval

Root cause: generated artifacts had local status but no global judge-owned promotion lifecycle.

Action: add promotion ledger and orchestration state.

Verification: tests assert existing PM/Architect/answer artifacts remain proposed until promoted.

### Issue 2 - cheap extraction work should not be done by judge or senior roles

Root cause: PM/Architect packs did not expose junior task packets and cost boundaries.

Action: add junior task packet builder with LOW-cost strict-context task contracts.

Verification: tests assert junior tasks have cost tier, forbidden actions, and no promotion authority.

### Issue 3 - proxy dry-run still trusted answer pack readiness without judge promotion

Root cause: answer pack status checked content readiness but not judge acceptance.

Action: require answer pack promotion status `ACCEPTED` before proxy dry-run readiness.

Verification: tests assert proxy refuses unpromoted answer pack and allows promoted answer pack.

## HANDLED

- Orchestration contract added.
- Junior task packet protocol added.
- Promotion ledger command added.
- Orchestration state builder added.
- Proxy dry-run promotion gate added.
- Tests added for judge control and delegation boundaries.

## CONFLICTS

### Auto-promotion of low-risk artifacts

- thesis: auto-promote READY packs to reduce friction
- antithesis: auto-promotion repeats the failure mode where generated artifacts become approval
- safe recommendation: no auto-promotion in this patch
- decision needed: revisit only after repeated real-HLD smoke success

### Real agent triggering

- thesis: trigger real agents now for faster feedback
- antithesis: real agents need invocation contracts and rollback handling
- safe recommendation: keep real agent triggering deferred until orchestration state is stable
- decision needed: approve future agent invocation contract patch
