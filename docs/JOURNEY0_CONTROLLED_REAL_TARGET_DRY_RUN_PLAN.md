# Journey 0 Controlled Real-Target Dry-Run Plan

Status: planning contract only / no execution

## Purpose: planning/gates only, no execution

This document defines the gates for a future controlled Journey 0 dry run against
an explicitly authorized real target. It does not execute a target, claim
real-target readiness, start Journey 1, wire the command surface, invoke SpecKit,
mutate targets, write HLD content, or create backlog or implementation scope.

## Scope and non-goals

Scope:

- define the future authorization and evidence gates
- define the target path and allowed-path requirements
- define the no-mutation proof expected from a future dry run
- define the expected report shape for human review

Non-goals:

- no real-target execution in this PR
- no command-surface wiring
- no Journey 1 HLD authoring or hardening
- no SpecKit execution
- no HLD writing
- no backlog creation
- no implementation planning or implementation

## Preconditions for future controlled dry run

A future real-target dry run may be prepared only after all of these are present:

- exact `target_root`
- exact `allowed_relative_paths`
- explicit run intent
- clean target snapshot before the run
- explicit acknowledgement that fixture proof is not real-target proof
- explicit acknowledgement that provenance remains a caveat
- explicit acknowledgement that the run cannot start Journey 1 or wire commands

## Run-intent gate

The future prompt must include:

- exact `target_root`
- exact `allowed_relative_paths`
- explicit run intent
- the forbidden actions

If `target_root`, `allowed_relative_paths`, or run intent are missing or
ambiguous, stop before reading target evidence.

## Target/allowed-path gate

The future run must use an explicit `target_root` and a non-empty
`allowed_relative_paths` list. Allowed paths must be relative, must stay under
`target_root`, and must not request broad or unbounded discovery.

If any path is absolute, escapes the target root, is missing, or requests an
unbounded scan, stop.

## Snapshot/no-mutation proof

The future run must record a before snapshot and an after snapshot for the
authorized scope. The report must include a no-mutation verdict.

If the before and after snapshots differ, stop and report mutation detected.

## Evidence rules

Journey 0 evidence is evidence, not authority. It may support a Journey 0
PASS/ACTION/BLOCKED verdict only through the typed Journey 0 artifacts.

Rules:

- declared product-surface evidence must be explicit
- generic file, doc, and code evidence is observational only
- generic file evidence must not be treated as PASS-capable by itself
- old specs are not backlog and not authority by default
- old specs must not preserve old spec boundaries as new feature boundaries
- conflicts and product-decision-required evidence block PASS
- `DEFERRED` product decisions block HLD writing

## Declared product-surface evidence rules

Declared product-surface evidence may support PASS only when the evidence is an
explicit human declaration with one of these source types:

- `product_capability`
- `product_actor`
- `product_input_output`
- `product_workflow`
- `product_limit`

Declared evidence records product-surface observations. It does not approve
product decisions, write HLD content, create backlog or implementation scope,
claim real-target readiness, or wire runtime behavior.

## Generic file/doc/code evidence limits

Structural observations from files, docs, code, tests, old SpecKit state, or HLD
fragments are useful evidence, but they are not product-surface declarations by
themselves. They must not create PASS alone.

## Product decision/conflict/deferred decision blockers

The future dry-run report must preserve blockers:

- OPEN product decisions block HLD writing
- DEFERRED product decisions block HLD writing unless a future safe deferral
  contract is explicitly approved
- CONFLICT evidence blocks PASS
- PRODUCT_DECISION_REQUIRED evidence blocks PASS
- HLD-code conflicts and safety/authority gaps block PASS

## Privacy/provenance caveats

Snippet content capture is disabled/safe by default for current collectors:
collected file evidence records structural metadata only. Provenance remains a
caveat for real-target execution.

The report must distinguish:

- fixture/local proof
- declared human evidence
- structural file evidence
- real-target evidence

The future dry run must not claim real-target readiness until it is actually
executed, verified, and reviewed.

## Stop conditions

Stop if any of these occur:

- dirty target
- missing or ambiguous `target_root`, `allowed_relative_paths`, or run intent
- unexpected path escape
- absolute allowed path
- unbounded evidence request
- snippet/privacy concern
- provenance ambiguity
- conflict/product decision/deferred decision
- mutation detected
- SpecKit requested
- HLD writing requested
- Journey 1 requested
- command wiring requested
- backlog or implementation scope requested

## Future dry-run report shape

The future report must include:

- target/run context (`target_root`, `allowed_relative_paths`, run intent)
- target path
- allowed path list
- evidence collected
- PASS/ACTION/BLOCKED result
- before/after snapshot result
- no-mutation verdict
- privacy/provenance caveats
- blockers and unresolved questions
- Journey 1 readiness: yes/no, with blockers
- next human decision

## What this does not authorize

This plan must not be used to:

- execute a real target
- claim real-target readiness
- start Journey 1
- wire command surface
- invoke SpecKit
- mutate targets
- write HLD content
- create backlog or implementation scope
- treat generic file evidence as PASS-capable
- treat old specs as authority/backlog
- hide provenance caveats or fixture/local limits

## Next review decision after a future dry run

After a future authorized dry run is executed and verified, the next review must
decide whether the result is:

- still blocked by provenance, conflicts, decisions, or insufficient evidence
- ready for another bounded dry run
- ready for a separate Journey 1 approval discussion

The dry run itself must not make the Journey 1 decision.
