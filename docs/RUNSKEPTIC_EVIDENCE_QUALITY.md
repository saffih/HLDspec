# RunSkeptic Evidence Quality

RunSkeptic findings must be evidence-complete before HLDspec uses them as blockers, fixes, or approval evidence.

Each finding or cycle must include:

```text
observed_evidence
evidence_level
confidence
unknowns
verification
residual_risk
```

## Statuses

```text
PASS
PENDING_HUMAN_REVIEW
REWORK_REQUIRED
```

## Meaning

`PASS` means every finding has evidence fields and no unresolved unknowns.

`PENDING_HUMAN_REVIEW` means evidence fields exist, but unknowns require a human decision.

`REWORK_REQUIRED` means at least one finding is missing required evidence fields.

## Command

```bash
uv run python scripts/review_runskeptic_evidence_quality.py \
  .hldspec-meta-review/hldspec_beskeptic_meta_review.json \
  --output-dir .hldspec-meta-review \
  --fail-on-rework
```

The review is read-only. It does not invoke SpecKit, does not run paid agents, and does not change source HLDs.
