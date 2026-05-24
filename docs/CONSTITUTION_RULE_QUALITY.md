# Constitution Rule Quality

HLDspec constitution/prework rules must be enforceable, not generic.

Each proposed rule must include:

```text
rule
rationale
HLD evidence
violation example
SpecKit phase enforced
affected artifacts
open question
```

## Statuses

```text
PASS
PENDING_HUMAN_REVIEW
REWORK_REQUIRED
```

## Meaning

`PASS` means every rule has enforceable fields and no unresolved open questions.

`PENDING_HUMAN_REVIEW` means the rule is structurally complete but needs a human decision.

`REWORK_REQUIRED` means at least one rule is missing required evidence or enforceability fields.

## Command

```bash
uv run python scripts/review_constitution_rule_quality.py \
  .specify/sync/constitution_update_plan.json \
  --output-dir .specify/sync \
  --fail-on-rework
```

The review is read-only. It does not invoke SpecKit and does not create final specs.
