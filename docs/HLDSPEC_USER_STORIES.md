# HLDspec User Stories and Acceptance Tests

Date: 2026-05-23

## Purpose

This file turns the product scenarios in `docs/HLDSPEC_USE_CASES_AND_API.md` into testable user stories.

## Story 1 - First run from raw HLD

As a user with a raw HLD, I want to run one HLDspec command so that the system inspects the HLD and stops at the first safe checkpoint.

Acceptance tests:

- GIVEN a raw HLD without HLDspec headings
- WHEN the user starts the public HLDspec facade with a source HLD and target workspace
- THEN HLDspec writes a format report
- AND writes a conversion plan
- AND writes a conversion decision queue
- AND does not invoke SpecKit
- AND does not create `.specify/memory/constitution.md`
- AND does not create `specs/*/spec.md`

## Story 2 - Conversion checkpoint

As a user, I want HLDspec to ask only necessary conversion questions so that raw HLD boundary decisions remain explicit.

Acceptance tests:

- GIVEN a raw HLD with ambiguous or very large candidate sections
- WHEN the conversion plan is built
- THEN blocking questions are written to `.specify/sync/hld_conversion_decision_queue.json`
- AND the markdown queue shows allowed answers
- AND HLDspec stops before plan/spec generation while blocking questions remain unresolved

## Story 3 - HLD section classification

As a user, I want HLDspec to distinguish buildable features from context so that business/stakeholder sections do not become SpecKit features.

Acceptance tests:

- GIVEN HLD sections titled Stakeholder Analysis, User Personas, Business Case Foundation, Executive Summary, Assumptions, and Milestones
- WHEN `scripts/classify_hld_sections.py` runs
- THEN those sections are classified as `HLD_CONTEXT_ONLY`
- AND they are not spec candidates
- GIVEN HLD sections titled Decision Log or Open Conflicts
- THEN those sections are classified as `GOVERNANCE`
- GIVEN a section titled Database API Interface
- THEN it remains `SPEC_CANDIDATE`

## Story 4 - Use-case/API map before SpecKit

As a user, I want HLDspec to show what it thinks the system does before SpecKit handoff so that wrong first-feature selection is caught early.

Acceptance tests:

- GIVEN a valid HLDspec HLD and section classification
- WHEN `scripts/build_hld_usecase_api_map.py <HLD.md> <workspace>` runs
- THEN `.specify/sync/hld_usecase_api_map.json` is written
- AND `.specify/sync/hld_usecase_api_map.md` is written
- AND the map includes actors, user journeys, system use cases, API/interface surfaces, data/source-of-truth objects, feature candidates, context-only sections, dependencies, non-goals, risks, and open questions
- AND context-only sections do not appear in feature candidates
- AND the first buildable feature is not context-only

## Story 5 - Spec build plan gate

As a user, I want HLDspec to prove the planner consumes classification so that context-only sections cannot become planned specs.

Acceptance tests:

- GIVEN a classified HLD where Stakeholder Analysis is not a spec candidate
- WHEN `hld_spec_sync.py --plan-specs` runs
- THEN Stakeholder Analysis is absent from `planned_specs`
- AND present in `context_hld_sections`
- AND a buildable API/data/processing section remains planned

## Story 6 - Prework approval package

As a user, I want one human-facing package before SpecKit invocation so that I can approve constitution, dependency order, first feature, and handoff evidence.

Acceptance tests:

- GIVEN a valid spec build plan and use-case/API map
- WHEN the prework package is built
- THEN it includes constitution case
- AND use-case/API case
- AND dependency case
- AND first feature case
- AND RunSkeptic findings
- AND feedback impact rules
- AND a human checkpoint

## Story 7 - Unsafe first feature blocked

As a user, I want HLDspec to block SpecKit handoff if the first feature is context-only so that implementation does not start from stakeholder or business context.

Acceptance tests:

- GIVEN a prework plan whose first feature source HLD section is listed in `context_only_sections`
- WHEN the prework quality gate runs
- THEN it emits a BLOCKER finding
- AND recommends rebuilding the spec build plan
- AND the prework package status is `REWORK_REQUIRED`

## Story 8 - Source-HLD-affecting feedback

As a user, I want architecture-changing feedback to be recorded as source-HLD-affecting so that HLDspec does not patch derived artifacts only.

Acceptance tests:

- GIVEN feedback that changes feature boundaries, dependency order, API split, or source-of-truth ownership
- WHEN HLDspec classifies the feedback
- THEN it records the feedback in a source update queue or decision log
- AND marks affected derived artifacts for rebuild
- AND does not modify the source HLD without explicit approval

## Story 9 - SpecKit proxy handoff

As a user, I want HLDspec to invoke one approved SpecKit phase for one approved feature so that context stays bounded and reversible.

Acceptance tests:

- GIVEN an approved feature queue and proxy dossier
- WHEN `hldspec_speckit_proxy.sh --feature <id> --phase specify` runs
- THEN exactly one feature is selected
- AND only bounded dossier context is used
- AND questions are answered only from HLD/prework evidence
- AND unknown architecture questions are escalated
- AND implementation is not run without explicit approval

## Story 10 - Status command

As a user, I want HLDspec to tell me where we are so that I do not need to inspect many artifacts manually.

Acceptance tests:

- GIVEN any HLDspec workspace
- WHEN `hldspec_status.sh` runs
- THEN it prints current stage
- AND current checkpoint
- AND controlling artifact
- AND whether human decision is needed
- AND next allowed action
