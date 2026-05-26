# Constitution Generation

## Purpose

This document defines how HLDspec creates a project-level constitution update plan for a target workspace.

The constitution is a stable rule set for the target app or domain. It must protect architecture, quality, testability, security, reliability, deployment safety, and source-of-truth discipline.

The constitution must not become a list of generated features.

## Core rule

The target constitution must be principle-level and guideline-level only.

It must not include:

- feature ids
- feature names
- feature order
- branch names
- task ids
- per-feature implementation details

Feature-specific information belongs in:

- `target/.hldspec/spec_packages.*`
- `target/.hldspec/feature_dependency_graph.*`
- `target/.hldspec/speckit_invocation_queue.*`
- `target/prompts/speckit/<feature>/*.md`

## Inputs

HLDspec may derive constitution signals from:

- source HLD
- `target/targetHLD/HLD.md`
- design docs
- architecture notes
- API/interface notes
- requirements
- testing requirements
- deployment constraints
- RunSkeptic findings
- human-approved decisions

## Required constitution sections

A generated constitution update plan should include:

1. Purpose
2. Source-of-truth rules
3. Architecture boundaries
4. Clean architecture principles
5. Interface and dependency rules
6. Design-for-testability rules
7. Unit testing requirements
8. Integration testing requirements
9. End-to-end or UI testing requirements where relevant
10. Quality gates
11. Multi-environment rules
12. Performance and reliability expectations
13. Security and input validation rules
14. Configuration and deployment rules
15. Verification and compliance rules
16. Constitution change process

## Rule format

Each constitution rule should use this shape when possible:

```text
Rule:
Rationale:
Source evidence:
Enforcement:
Verification:
Owner:
```

## Required properties

Constitution rules must be:

- specific
- actionable
- verifiable
- consistent
- traceable to evidence or approved defaults
- stable across features

## Architecture protection

The constitution must define:

- canonical source-of-truth documents
- system boundaries
- ownership boundaries
- interface boundaries
- data ownership rules
- required approval for deviations
- how conflicts are escalated

## Clean architecture

The constitution should prefer:

- dependency inversion
- explicit interfaces
- ports/adapters where useful
- business logic separated from infrastructure
- dependency injection over hidden global state
- small bounded modules
- clear ownership of side effects

## Design for testability

The constitution must require testability as a first-class design concern.

Rules must cover:

- external dependencies behind interfaces
- deterministic controls for time, randomness, I/O, and external systems
- mocks, fakes, stubs, and spies strategy
- test data factories, builders, or fixtures
- unit, integration, and end-to-end test seams
- observability needed for verification

## Testing standards

The constitution must require every implementation package to define:

- unit test expectations
- integration test expectations
- end-to-end testability path where relevant
- negative and edge case testing
- test data requirements
- command or process proving the package is green
- command or process proving the full system is still green

If test tools are missing, the package must either create the approved test harness or block for approval.

## Quality gates

The constitution must define stage gates such as:

- pre-commit
- pre-merge
- pre-release
- staging validation
- production promotion

Gates should be mechanically enforced where possible.

## RunSkeptic integration

RunSkeptic is required when a rule touches:

- architecture boundary
- source of truth
- dependency order
- API contract
- data ownership
- security
- reliability
- testability
- quality gates
- significant implementation risk

Missing evidence must be classified as ACTION or CONFLICT, not PASS.

## Output artifacts

HLDspec must produce:

- `target/.hldspec/constitution_signals.json`
- `target/.hldspec/constitution_update_plan.json`
- `target/.hldspec/constitution_update_plan.md`

HLDspec must not update `target/.specify/memory/constitution.md` without explicit approval.

## Acceptance criteria

- The constitution is short enough to be used.
- The constitution covers all critical constraints.
- The constitution is not feature-specific.
- Every rule has evidence, rationale, or an explicit approved default.
- Verification is clear.
- Conflicts are escalated, not silently resolved.
