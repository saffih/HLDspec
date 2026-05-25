# ADR-004: Approval is a typed state transition

**Status:** ACCEPTED  
**Date:** 2026-05-25  

## Context

Human approval was originally expressed as prose: the user typed "ok", "accept", "next", or similar, and the system parsed this loosely to decide whether to continue. This made approval semantically ambiguous. Different humans might type different words for the same intent. The same word might mean different things at different checkpoints. There was no machine-readable record of what was approved, who approved it, when, or on what evidence.

This is a traceability problem as much as an implementation problem. If a later stage fails, there is no reliable record of what the human actually reviewed and accepted at earlier gates.

## Decision

Human approval is a typed artifact with a defined structure: `decision`, `decision_owner`, `rationale`, `affected_artifacts`, `timestamp`, and `evidence_reviewed`. Machines refuse continuation without a valid approval artifact at checkpoints that require human approval.

The `reply_parser.py` module maps human input to typed decisions. It does not pass prose directly to downstream logic. An approval is not "accepted" until it is recorded as a structured artifact. Prose input that cannot be mapped to a known decision type is rejected with a request for clarification.

## Consequences

- `reply_parser.py` produces typed decisions; it does not emit raw strings for downstream interpretation.
- Prose alone cannot gate continuation at any checkpoint that requires approval.
- Every approval is traceable: the artifact records what was decided, by whom, at what time, and what evidence was reviewed.
- Adding a new decision type requires updating `reply_parser.py` and the relevant machine's accepted decisions list.
- Automated testing can validate approval flow without human input by constructing typed approval artifacts directly.
