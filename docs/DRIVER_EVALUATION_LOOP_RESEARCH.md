# Driver Evaluation Loop Research

**Status:** supporting research/conclusion record. It is not an implementation
contract.

## Status

- This is a research/conclusion record, not an implementation contract.
- It follows the first live E2E proof architecture alignment.
- It does not add runtime behavior.

## Current Conclusion

- Driver owns route integrity.
- Helper owns toolchain-specific commands/actions.
- RunSkeptic is a checkpoint/evaluator tool.
- Human owner owns protected approvals.

## Research Findings

- First live proof is real but narrow.
- The proof is a controlled brownfield fixture, not arbitrary brownfield support.
- Smoke is a recognition/model-obedience probe, not a safety proof.
- Concrete SpecKit commands are `/speckit-*`.
- Dot-style `/speckit.*` is abstract shorthand only, not installed command spelling.
- The readiness doctor is diagnostic/propose-only.
- The live proof harness is sandbox proof mode only.
- Driver v0 is read-only and has no execution channel.
- A system driver may replace the human operator, not the human approver/owner.

## Driver Evaluation Loop Candidate

The future Driver Evaluation Loop should:

1. Observe state.
2. Classify journey and phase.
3. Check helper recommendation, selection, and effective helper.
4. Check installed runtime/helper identity.
5. Check authority and protected boundaries.
6. Check required evidence.
7. Run deterministic tests or evidence checks where available.
8. Run RunSkeptic when a checkpoint requires it.
9. Classify `PASS` / `ACTION` / `BLOCKED` / `CONFLICT`.
10. Emit the next safe action.
11. Stop at the protected owner boundary.

This is a candidate evaluation loop only. It does not authorize execution,
mutation, promotion, or approval.

## RunSkeptic Checkpoint Placement

RunSkeptic should be required:

- before promotion between journey stages;
- after helper output;
- before implementation approval;
- before merge/commit/push readiness; and
- when contradiction, command drift, scope expansion, failed tests, or stale
  evidence appears.

## Trade-offs

- **Autonomy vs route integrity:** an autonomous path can reduce interaction but
  makes it easier to cross protected boundaries; route integrity dominates until
  a separately approved authority model exists.
- **Generic driver vs helper-specific detail:** the driver should evaluate shared
  state and boundaries, while the helper remains the owner of toolchain-specific
  commands and evidence.
- **RunSkeptic everywhere vs checkpoint-triggered RunSkeptic:** running it for
  every observation is costly and noisy; checkpoint-triggered evaluation preserves
  scrutiny at promotion and contradiction boundaries.
- **Repeated live proof vs cost/rate-limit constraints:** more live evidence would
  increase confidence, but token, rate-limit, and side-effect costs require a
  safer readiness probe and fixture suite before repetition.

## Not Decided Yet

The following are follow-ups, not implemented:

- Driver Evaluation Loop contract;
- safer non-stateful readiness/smoke probe;
- brownfield fixture suite;
- approved execution authority; and
- system-operator mode.

## Recommended Sequencing

9. Merge PR #22 proof/command/authority alignment.
10. Design safer non-stateful readiness/smoke probe.
11. Add Driver Evaluation Loop / RunSkeptic checkpoint contract.
12. Add brownfield fixture suite.
13. Only later consider approved execution authority.
