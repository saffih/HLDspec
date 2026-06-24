# SpecKit Helper Execution Contract

**Status:** contract and anti-drift checks only. This is not runtime SpecKit
execution, a new execution channel, a bridge, a command envelope, or a target
mutation mechanism.

## Purpose

This contract makes a future SpecKit helper bypass observable and blocked. It
does not authorize execution. The driver checks declared receipts and proposes
the next safe action; the human owner retains protected approval.

The phase notation in this document is:

```text
/specify → /analyze → /plan → /tasks → implementation/testing
```

It names contract phases, not concrete installed command spelling and not an
instruction to execute a command. Concrete installed command identity remains
the repository's `/speckit-*` form. This contract does not alter the existing
Journey 3 lifecycle.

The current Journey 3 lifecycle has a different documented phase order. Before
any runtime adopts this candidate sequence, the canonical lifecycle must be
reconciled through an explicit human owner decision. Until then, a runtime must
return `STOP / CANONICAL_SEQUENCE_RECONCILIATION_REQUIRED` rather than treating
this document as an override.

## Transition Rules

No receipt → no transition.

No prerequisite phase → no next phase.

No SpecKit availability → STOP.

No human approval for protected transition → STOP.

| Requested transition | Required current receipt | Result when absent or invalid |
|---|---|---|
| `/specify` to `/analyze` | `SPECIFY_RECEIPT` | `STOP / MISSING_SPECIFY_RECEIPT` |
| `/analyze` to `/plan` | `ANALYZE_RECEIPT` | `STOP / MISSING_ANALYZE_RECEIPT` |
| `/plan` to `/tasks` | `PLAN_RECEIPT` | `STOP / MISSING_PLAN_RECEIPT` |
| `/tasks` to implementation/testing | `TASKS_RECEIPT` and human approval | `STOP / MISSING_TASKS_RECEIPT` or `STOP / HUMAN_APPROVAL_REQUIRED` |

Each receipt must identify the target, its source evidence identity, phase, and
creation time. A stale receipt is rejected. A receipt for a different target is
rejected. A receipt only establishes a phase transition; it is not implementation
approval.

## Availability and Authority

If SpecKit is unavailable, the result is `STOP / SKILL_UNAVAILABLE`. There is no
manual fallback, alternate toolchain fallback, inferred receipt, or silent
continuation. Manual fallback is not a valid substitute for missing SpecKit
availability or missing phase receipts.

At `GUIDE_ONLY`, the driver can inspect evidence and recommend a next action,
but cannot execute SpecKit, write a target, or create a phase receipt. The driver
recommends but does not approve. Implementation/testing remains a protected
transition requiring explicit human owner approval.

## Bypass Detection

The contract requires negative tests for every attempted phase bypass:

- analyze without a current `SPECIFY_RECEIPT`;
- plan without a current `ANALYZE_RECEIPT`;
- tasks without a current `PLAN_RECEIPT`;
- implementation/testing without a current `TASKS_RECEIPT`;
- stale receipt;
- wrong-target receipt;
- missing SpecKit availability; and
- any manual fallback claim.

A bypass is `STOP`, never an implied PASS. A future executor may be introduced
only by a separate approved slice that implements validation and authority
controls; this contract itself has no execution channel.

## Boundaries

This slice does not invoke SpecKit, create work orders, mutate target repos or
product code, write `.specify/`, implement a bridge, or implement a command
envelope. It is a documentation-and-test contract that future runtime work must
satisfy before it can claim a safe transition.
