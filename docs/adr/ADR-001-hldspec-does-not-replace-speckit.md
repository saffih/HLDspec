# ADR-001: HLDspec does not replace SpecKit

**Status:** ACCEPTED  
**Date:** 2026-05-25  

## Context

HLDspec exists to prepare the context needed for SpecKit to operate correctly. It extracts PM and architecture artifacts from a source HLD, validates their quality, orders features by dependency, and gates the workflow at defined checkpoints. SpecKit is the downstream system that actually authors specification artifacts.

There is a risk that, over time, HLDspec could accumulate responsibilities that belong to SpecKit — writing spec files, deciding spec content, or invoking SpecKit commands directly as part of its own pipeline. This would blur the boundary between preparation and authorship, creating coupling that makes both systems harder to change independently.

## Decision

HLDspec machines gate and order. SpecKit owns spec artifacts. HLDspec prepares and validates the prework package; it does not write final specification documents and does not invoke SpecKit commands directly. The handoff is a documented artifact package passed at the `SPECKIT_PREWORK_APPROVAL_GATE` checkpoint, not a programmatic function call into SpecKit.

The `SpecKitExecutionMachine` is the only machine permitted to interface with SpecKit, and it does so only after the prework approval gate is passed. Even that machine does not write spec content — it sequences SpecKit invocations and tracks execution state.

## Consequences

- HLDspec may never write final spec artifacts directly.
- HLDspec may never invoke SpecKit commands outside the `SpecKitExecutionMachine`.
- Any feature request that causes HLDspec to author spec content is out of scope and must be rejected.
- The boundary between HLDspec output (prework package) and SpecKit input (prework package) must remain a documented, versioned artifact contract.
