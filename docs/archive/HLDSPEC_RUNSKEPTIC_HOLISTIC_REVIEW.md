# HLDspec Holistic RunSkeptic Review

Date: 2026-05-23

## Source of truth

RunSkeptic source read before this review:

- Repository: saffih/skeptic
- File: skeptic.md
- Required flow: GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN

## Scope

Whole product flow:

```text
Raw HLD -> conversion -> classification -> use-case/API map -> spec build plan -> prework gate -> human approval -> SpecKit proxy
```

## GATE

DONE is testable when:

- Formal user stories and acceptance tests exist.
- HLDspec generates an executable use-case/API map.
- The first read-only flow produces the map before prework package generation.
- The prework package presents the use-case/API case.
- The quality gate can detect a context-only first feature when the map exists.
- The remaining gap to the product goal is explicit.

Scope is tractable because this patch adds one executable builder, focused tests, and documentation.

Wrong-answer cost is acceptable because this is still read-only prework. It does not invoke SpecKit and does not modify the source HLD.

Decision: FIX allowed for the map and documentation layer. DECOMPOSE SpecKit proxy and interview wrappers.

## FUNDAMENTAL SCAN

Purpose:

- HLDspec should behave like a judge-led product, not a loose collection of scripts.

Architecture shape:

- Raw HLD inspection creates conversion evidence.
- HLD section classification identifies context versus buildable candidates.
- Use-case/API map explains the system and separates context from implementable features.
- Spec build plan turns buildable sections into candidate SpecKit features.
- Prework quality gate blocks unsafe handoff.
- Human approval precedes SpecKit invocation.

Boundaries:

- HLDspec owns extraction, classification, planning, gates, state, and handoff dossiers.
- SpecKit owns spec.md, plan.md, tasks.md, and implementation artifacts.
- Source HLD remains the design source of truth.

Structural issue:

- The product scenarios existed, but the use-case/API map was only documented, not executable.

## MAP

### Charlie Munger (CH) - Systems, Dependencies, Failure

Finding:

- Prework depends on feature selection. Without a use-case/API map, a wrong first feature can pass through as plausible plan text.

### Occam's Razor (OM) - Necessity, Simplicity, Boundaries

Finding:

- A read-only derived map is the smallest useful product layer before wrappers or SpecKit proxy.

### Richard Feynman (FE) - Honesty, Explanation, Reality

Finding:

- The repo had documented scenarios, but not formal user stories or executable map artifacts. The gap should be stated directly.

### Karl Popper (PO) - Falsification, Contradiction, Unsafe Change

Finding:

- A simple falsifier exists: Stakeholder Analysis must appear in context-only sections and not in feature candidates; Session API must remain a feature candidate.

### Immanuel Kant (KT) - Universalizability

Finding:

- Every product layer should have a user story and acceptance test before deeper orchestration is added.

### Saffi (SH) - Sharp Trade-off Heuristics

Finding:

- Side A: implement full product wrappers now. Side B: add the missing executable map and tests first. Side B should dominate because wrappers without the map would automate an incomplete decision basis.

## CONFIDENCE

Detection confidence: adequate.

Evidence:

- Product scenarios are documented in `docs/HLDSPEC_USE_CASES_AND_API.md`.
- Current TODO already lists the use-case/API map as the next patch.
- Current stabilization record explicitly deferred the map until planner confidence was proven.
- The new builder has focused regression tests.

Unknowns:

- Full Flow HLD end-to-end behavior still requires local project verification.
- Actor/journey extraction is heuristic and must not be treated as semantic proof.
- The future state artifact and interview loop are not implemented yet.

Skipped areas:

- SpecKit proxy execution.
- Full interactive interview loop.
- Source-HLD feedback queue implementation.

## STABILIZE

### Stabilized issue 1

Issue:

- Product scenarios were documented but not formalized as user stories with acceptance tests.

Root cause:

- Design doc described behavior, but execution tracking needed testable story format.

Action:

- Add `docs/HLDSPEC_USER_STORIES.md`.

### Stabilized issue 2

Issue:

- Use-case/API map was documented but missing as an executable artifact.

Root cause:

- Earlier patches correctly fixed classifier and planner gates first.

Action:

- Add `scripts/build_hld_usecase_api_map.py`.
- Generate `.specify/sync/hld_usecase_api_map.json` and `.md`.
- Wire it into first read-only flow after classification and before spec build plan.

### Stabilized issue 3

Issue:

- Prework package did not present the use-case/API case.

Root cause:

- The package was built before the executable map existed.

Action:

- Include use-case/API case in prework package JSON and markdown.

### Stabilized issue 4

Issue:

- Quality gate could not use the map to catch a context-only first feature.

Root cause:

- No map artifact existed to compare feature sources against context-only HLD sections.

Action:

- Add quality finding when the first feature source overlaps context-only map sections.

## EVIDENCE

- Issue 1 evidence level: OBSERVED.
- Issue 2 evidence level: OBSERVED and REPRODUCED by tests after patch.
- Issue 3 evidence level: OBSERVED and REPRODUCED by generated package after patch.
- Issue 4 evidence level: OBSERVED and testable by constructing a bad plan/map pair.

## DECIDE

HANDLED:

1. User stories and acceptance tests.
   - Decision: FIX.
   - Verification: file exists and lists testable acceptance criteria.

2. Executable use-case/API map.
   - Decision: FIX.
   - Verification: focused unittest and first-run wiring.

3. Prework package use-case/API case.
   - Decision: FIX.
   - Verification: package includes `use_case_api_case`.

4. Quality gate context-only first-feature detection.
   - Decision: FIX.
   - Verification: code path checks first feature sources against map context-only sections.

CONFLICTS:

1. Full SpecKit proxy readiness.
   - Thesis: implement now to complete the product loop.
   - Antithesis: proxy requires approved feature queue, state artifact, and bounded dossier semantics to be stable first.
   - Tradeoffs: faster product completeness versus unsafe automation.
   - Blocking unknowns: exact SpecKit command contract, answer escalation lifecycle, and approval persistence.
   - Missing evidence: no proxy end-to-end test.
   - Safe recommendation: defer to a later patch.
   - Decision needed: approve proxy scope after state/status/interview layer exists.

2. Unknown section default.
   - Thesis: default unknown HLD sections to REVIEW_NEEDED to avoid false features.
   - Antithesis: defaulting to SPEC_CANDIDATE preserves coverage until use-case/API map proves a safer review path.
   - Tradeoffs: fewer false positives versus risk of losing real buildable work.
   - Blocking unknowns: how many real HLDs rely on unknown-title sections being planned.
   - Missing evidence: broad sample corpus.
   - Safe recommendation: keep current default until more false positives appear.
   - Decision needed: revisit after testing on Flow HLD.

## ACT

Applied in this patch:

- Formal user stories and acceptance tests.
- Executable use-case/API map builder.
- First read-only flow wiring.
- Prework package use-case/API case.
- Quality gate map-aware checks.
- Focused use-case/API map regression test.

## VERIFY

Required commands:

```bash
python3 -m py_compile scripts/build_hld_usecase_api_map.py
python3 -m py_compile scripts/build_speckit_prework_package.py
python3 -m py_compile scripts/build_speckit_prework_quality_review.py
python3 -m unittest discover -s tests -p 'test_hld_usecase_api_map.py'
python3 -m unittest discover -s tests
git diff --check
```

Manual spot checks:

- Stakeholder Analysis appears in context-only sections.
- Stakeholder Analysis does not appear in feature candidates.
- Session API appears in feature candidates.
- `hld_usecase_api_map.md` appears in first-run output list.
- Prework package includes a Use-case/API case.

## LEARN

Double-loop trigger remains active:

- If context-only false positives keep appearing, reconsider the unknown default and add stronger review-needed classification.
