# First Live E2E Proof

**Status:** supporting architectural evidence record. This document records the
first verified live proof without promoting it into a general execution claim.

## Status

- **First Live E2E Proof achieved.**
- **Reference model:** Opus.
- **Target:** `/tmp/proof-target`.
- **Proof type:** controlled brownfield fixture.

## Proven

- HLDspec can drive one bounded, SpecKit-backed live implementation proof through
  the existing proof harness and invoker.
- Opus can make the surgical calculator change: preserve `add`, add
  `subtract(a, b) -> a - b`, expose it from `calc/__init__.py`, and add the
  corresponding test.
- A bounded diff plus target `pytest` can verify the result: target `pytest`
  returned `2 passed`.
- The proof did not require a global Claude configuration mutation. SpecKit init
  occurred only inside `/tmp/proof-target`.

## Exact Expected Target Diff

The final Opus proof changed exactly:

- `calc/core.py`
- `calc/__init__.py`
- `tests/test_core.py`

No `specs/` mutation or stray branch was part of the final proof.

## Not Proven

This single fixture does **not** prove:

- arbitrary brownfield repository support;
- production autonomy or autonomous execution;
- weak-model reliability, including Haiku reliability;
- side-effect-free smoke behavior;
- multi-helper support;
- SourceBinding, ISG Governance, READY, or NextActionPacket behavior; or
- a broad execution channel or a production execution channel.

## Command Identity

Concrete installed SpecKit commands use the `/speckit-*` style, including
`/speckit-specify`, `/speckit-plan`, `/speckit-tasks`, `/speckit-analyze`, and
`/speckit-implement`.

Dot-style `/speckit.*` must not be used as the spelling of a concrete installed
command. When it appears in architecture text, it is abstract command-family
shorthand only. The concrete command spelling remains `/speckit-*`.

## Smoke Limitation

Smoke is a recognition and model-obedience probe, not proof of safe skill
execution. `/speckit-specify` is stateful, and weak models can trigger workflow
side effects. A smoke result is therefore not guaranteed side-effect-free and
does not establish that a live skill run is safe.

A safer readiness/smoke probe is a follow-up item; it must be designed and
verified separately from this proof record.

## Authority Boundary

The live proof harness is sandbox proof mode for `/tmp/proof-target` only. It is
not Journey 3 default authority. It is not a production execution channel and
not autonomous execution. It does not establish permission to execute against
any other target.

## Driver Implications

- **Driver** owns route integrity: it checks state, sequence, evidence, and the
  next safe route.
- **Helper** owns toolchain-specific commands and actions.
- **RunSkeptic** is a checkpoint and evaluator tool; it is not an execution
  authority.
- The **Human owner** retains protected approvals.

A future Driver Evaluation Loop may use this evidence as input, but it is a
follow-up and is not implemented by this slice.
