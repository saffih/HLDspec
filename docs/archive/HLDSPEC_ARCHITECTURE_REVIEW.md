# HLDspec Architecture Review

This review applies Uncle Bob / SOLID design pressure with RunSkeptic evidence fields before large refactors.

## Purpose

Do not perform broad refactors by intuition.

First generate an evidence-backed architecture review:

```bash
uv run python scripts/review_hldspec_architecture.py \
  --repo . \
  --output-dir .hldspec-architecture-review
```

## Lens

```text
SRP: one reason to change per script/module.
OCP: new checkpoint/review behavior should extend renderer/reviewer contracts, not rewrite shell prose.
DIP: shell runners depend on stable Python CLIs, not embedded Python/heredoc implementation details.
ISP: renderer, reviewer, builder, and orchestrator contracts stay narrow.
Testability: behavior tests verify rendered output and JSON contracts, not brittle implementation strings.
```

## Required RunSkeptic evidence fields

Each finding must include:

```text
observed_evidence
evidence_level
confidence
unknowns
verification
residual_risk
```

## Refactor rule

Fix one seam per patch.

Recommended order:

```text
1. Characterization test for current behavior.
2. Extract one responsibility.
3. Keep CLI/output compatibility.
4. Run narrow tests.
5. Run full tests.
6. Commit only intended files.
```

## Non-goals

```text
- Do not invoke SpecKit.
- Do not implement app code.
- Do not modify source HLDs.
- Do not rewrite unrelated scripts in one patch.
```
