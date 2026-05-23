# HLDspec RunSkeptic Stabilization Record

made by AI

Date: 2026-05-23

## Source of truth

RunSkeptic source read before this patch:

- Repository: saffih/skeptic
- File: skeptic.md
- Required flow: GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN

## Scope

This stabilization covers the next safe patch after the classifier false-positive fix.

In scope:

- HLD section classification consumption by the spec build planner.
- Plan-level regression coverage for context-only sections.
- Plan quality decision semantics when there are no findings or conflicts.
- Implementation TODO/status tracking.

Out of scope:

- Executable hld_usecase_api_map builder.
- Interview wrapper.
- hldspec_state artifact.
- SpecKit proxy execution.

## GATE

DONE is testable:

- A context-only HLD section must not appear in planned_specs.
- The same section must appear in context_hld_sections.
- A buildable API section must still appear in planned_specs.
- A clean plan must report PASS / KEEP_PLAN, not FIX / KEEP_PLAN.

Scope is tractable:

- One production file.
- One focused test file.
- Two documentation files.

Wrong-answer cost is acceptable:

- Patch is read-only planning behavior plus tests and docs.
- No source HLD mutation.
- No SpecKit invocation.

Decision: FIX allowed.

## FUNDAMENTAL SCAN

Purpose:

- HLDspec should prevent non-buildable HLD context from becoming the first SpecKit feature.

Architecture shape:

- classify_hld_sections.py writes hld_section_classification.json.
- hld_spec_sync.py --plan-specs reads the classification file.
- build_spec_build_plan either plans a section or preserves it in context_hld_sections.

Boundaries:

- Classifier decides section kind.
- Planner enforces whether a section can become a planned spec.
- Prework/use-case/API mapping remains a later layer.

Source of truth:

- HLD.md remains the design source of truth.
- hld_section_classification.json is a derived planning input.
- spec_build_plan.json is the derived handoff plan.

Structural finding:

- The classifier fix is necessary but incomplete without a planner-level regression test.

## MAP

### Charlie Munger (CH) - Systems, Dependencies, Failure

Finding:

- Downstream prework depends on spec_build_plan correctness. If the planner ignores classification, the classifier fix gives false confidence.

### Occam's Razor (OM) - Necessity, Simplicity, Boundaries

Finding:

- A focused plan-level regression is simpler and safer than adding hld_usecase_api_map now.

### Richard Feynman (FE) - Honesty, Explanation, Reality

Finding:

- The code path is visible, but without a committed test the behavior is not proven by the repo.

### Karl Popper (PO) - Falsification, Contradiction, Unsafe Change

Finding:

- The falsifier is simple: create an HLD with Stakeholder Analysis and Session API. The test fails if Stakeholder Analysis appears in planned_specs or is missing from context_hld_sections.

### Immanuel Kant (KT) - Universalizability

Finding:

- Every classifier rule that affects planning should have at least one planner-level regression when the downstream risk is feature mis-selection.

### Saffi (SH) - Sharp Trade-off Heuristics

Finding:

- Side A: move fast to product wrappers. Side B: prove planner correctness first. Side B should dominate until the handoff gate is stable. The exception is documentation that records the product roadmap.

## CONFIDENCE

Detection confidence: adequate.

Evidence:

- Classifier terms and tests exist.
- Planner code reads hld_section_classification.json and writes context_hld_sections.
- Missing plan-level regression is directly observable.
- Plan quality currently uses FIX / KEEP_PLAN when no findings exist.

Unknowns:

- Full Flow HLD behavior still needs local end-to-end verification after this patch.
- Larger use-case/API map extraction boundaries are not yet implemented.

Skipped areas:

- SpecKit proxy behavior.
- Interactive interview loop.
- hldspec_state lifecycle.

## STABILIZE

### Stabilized issue 1

Issue:

- The classifier fix lacks committed downstream proof at the planner boundary.

Root cause:

- Missing regression test for classification consumption by build_spec_build_plan.

Action:

- Add tests/test_hld_spec_build_plan_context_gate.py.

### Stabilized issue 2

Issue:

- Clean plan quality reports FIX / KEEP_PLAN.

Root cause:

- apply_plan_quality has no PASS state for the no-findings path.

Action:

- Change the no-findings/no-conflicts branch to PASS / KEEP_PLAN.

### Stabilized issue 3

Issue:

- TODO/product readiness is not tracked as an execution artifact.

Root cause:

- Product direction exists in design docs, but current done/next/deferred status is not explicit.

Action:

- Add docs/HLDSPEC_IMPLEMENTATION_TODO.md.

## EVIDENCE

- Issue 1 evidence level: OBSERVED and REPRODUCED after the new test passes.
- Issue 2 evidence level: OBSERVED and REPRODUCED after the new test passes.
- Issue 3 evidence level: OBSERVED.

## DECIDE

HANDLED items:

1. Planner-level confidence gap.
   - Decision: FIX.
   - Verification: focused plan-level unittest plus full unittest discovery.

2. Plan-quality semantics.
   - Decision: FIX.
   - Verification: focused unittest asserts PASS / KEEP_PLAN for clean plan.

3. TODO/status gap.
   - Decision: FIX.
   - Verification: documentation file exists and is included in diff.

CONFLICTS:

1. Whether to implement the use-case/API map in this same patch.
   - Thesis: implement now to move closer to product use.
   - Antithesis: defer until planner confidence is proven.
   - Tradeoffs: faster product progress vs lower blast radius and clearer failure isolation.
   - Blocking unknowns: extraction boundary and prework gate contract are not yet tested.
   - Missing evidence: no executable hld_usecase_api_map tests yet.
   - Safe recommendation: defer to next patch.
   - Decision needed: approve Patch 3 scope after Patch 2 passes.

## ACT

Applied changes:

- hld_spec_sync.py clean plan-quality branch now returns PASS / KEEP_PLAN.
- Added tests/test_hld_spec_build_plan_context_gate.py.
- Added docs/HLDSPEC_IMPLEMENTATION_TODO.md.
- Added this RunSkeptic stabilization record.

## VERIFY

Patch script verification commands:

```bash
python -m py_compile hld_spec_sync.py
python -m py_compile scripts/classify_hld_sections.py
python -m py_compile tests/test_hld_spec_build_plan_context_gate.py
python -m unittest discover -s tests -p 'test_hld_spec_build_plan_context_gate.py'
python -m unittest discover -s tests -p 'test_hld_section_classification_context.py'
python -m unittest discover -s tests
git diff --check
```

Manual spot checks:

- Stakeholder Analysis is classified as HLD_CONTEXT_ONLY.
- Stakeholder Analysis is absent from planned_specs.
- Stakeholder Analysis is present in context_hld_sections.
- Session API remains in planned_specs.
- Clean plan quality is PASS / KEEP_PLAN.

## LEARN

No double-loop change yet.

Trigger for double-loop later:

- If more context-only false positives appear after the use-case/API map exists, reconsider defaulting unknown sections to SPEC_CANDIDATE.
