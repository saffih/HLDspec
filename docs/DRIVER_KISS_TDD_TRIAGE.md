# Driver KISS/TDD Triage

**Status:** contract and anti-drift checks only. This document adds no runtime
behavior, execution channel, target mutation, or product-code mutation.

## Default Rule

The driver defaults to KISS and TDD. It may permit complexity only when a current, evidenced concern makes the simple approach unsafe or insufficient. Speculation, future-proofing, and agent preference are not valid complexity justifications.

The default is `KISS_REQUIRED` + `TDD_REQUIRED` + smallest safe slice. The
driver records its recommendation and evidence; it does not approve a protected
transition or execute an implementation.

## Triage Decisions

| Work shape or evidence | Required decision | Required validation | Stop condition |
|---|---|---|---|
| Proof of concept (POC) | `KISS_REQUIRED` | Smallest behavior-focused test | Current risk evidence is absent |
| Simulator | `KISS_REQUIRED` | Smallest deterministic behavior-focused test | Current risk evidence is absent |
| Documentation-only change | `KISS_REQUIRED` | `DOC_CHECK_REQUIRED` (doc/grep/link check), not a fake code test | The documentation claim lacks evidence |
| Complexity request with `CURRENT_EVIDENCED_RISK` | `COMPLEXITY_PERMITTED` | Test that covers the named risk | Risk is stale, speculative, or unrelated |
| Complexity request based on future-proofing, speculation, or agent preference | `BLOCKED` | None; simplify or obtain current evidence | No current evidenced concern |
| No failing check or other current failure evidence | `NO_IMPLEMENTATION` | Diagnose or add the smallest relevant check first | Implementation is requested anyway |
| Protected authority boundary | `SKEPTIC_ESCALATION_REQUIRED` | RunSkeptic evidence plus human owner approval | Approval is absent |

`CURRENT_EVIDENCED_RISK` means a present, target-specific concern supported by a
failing check, observed failure, current contract conflict, or comparable durable
evidence. A hypothetical future need is not evidence.

## TDD and Smallest Slice

- A behavior-changing slice requires a failing or otherwise current check before
  implementation is recommended.
- The recommended change must be the smallest slice that addresses the current
  evidence.
- Documentation-only work uses `DOC_CHECK_REQUIRED`; it must not invent a code
  test merely to imitate TDD.
- A POC or simulator is not an automatic license for architecture. Both begin
  `KISS_REQUIRED` unless current evidence proves the simple approach unsafe or
  insufficient.

## Driver Output and Authority

Every driver recommendation records:

- `kiss_tdd_decision`;
- `current_evidence`;
- `required_check`;
- `skeptic_level`; and
- `next_safe_action`.

The driver may recommend a slice and its validation. The driver does not approve
implementation, complexity, protected transitions, commits, pushes, or merges.
When a recommendation crosses an authority boundary, the required output is
`SKEPTIC_ESCALATION_REQUIRED` and the next safe action is human owner review.

This contract preserves `GUIDE_ONLY`: it cannot execute a command, mutate a
target, or substitute for the human approver/owner.

## Boundaries

This is not a new helper, executor, bridge, command envelope, or target control
surface. It does not invoke SpecKit, create work orders, write `.specify/`, or
alter the existing Journey 3 runtime lifecycle. Future execution authority needs
a separately approved implementation and is outside this slice.
