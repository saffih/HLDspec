# Product QA Loop Driver Slice 2A — Ledger Row Classifier

## Purpose

Classify rows from the product QA feature ledger into one of 8 categories.
A classification is not a work order and is not implementation approval.

## Input / Output

| Artifact | Location | Owner |
|---|---|---|
| **Input**: `feature-ledger.json` | `<target>/qa/feature-ledger.json` | target (product QA) |
| **Output**: `product-ledger-classification.json` | `<control_sync>/product_qa_loop/` | control-plane |
| **Output**: `product-ledger-classification.md` | `<control_sync>/product_qa_loop/` | control-plane |

The classifier **reads** the target-owned ledger. It **writes** only to the control-plane.
It does not modify the ledger, invoke SpecKit, create work orders, or touch product code.

---

## Classification Values

```python
VALID_CLASSIFICATIONS = frozenset({
    "NO_ACTION",
    "NEEDS_EXPECTED_BEHAVIOR",
    "BUGFIX_CANDIDATE",
    "UX_FIX_CANDIDATE",
    "HARNESS_FIX_CANDIDATE",   # reserved — not assigned in Slice 2A (no clean signal)
    "SPEC_GAP_CANDIDATE",
    "PRODUCT_DECISION_REQUIRED",
    "BLOCKED_NO_EVIDENCE",
})
```

`HARNESS_FIX_CANDIDATE` is a valid classification value but is **not assigned by any rule in Slice 2A**.
It is reserved for future use when explicit harness/tooling evidence is available (e.g. a dedicated
`blocked_reason` field or harness-specific `defect_category`). In Slice 2A, `status == "blocked"` routes
to `PRODUCT_DECISION_REQUIRED`.

---

## Classification Decision Table

The table is **total**: every possible row maps to exactly one classification.
Rules are evaluated in priority order; first match wins.

### Priority order

| # | Rule | Classification | Rationale |
|---|---|---|---|
| 1 | `evidence` is empty/blank | `BLOCKED_NO_EVIDENCE` | No evidence = cannot classify. Fail closed. |
| 2 | `status` and `test_status` contradict (e.g. `status=fail` + `test_status=PASS`) | `PRODUCT_DECISION_REQUIRED` | Conflicting signals need human resolution. |
| 3 | `approval_needed == True` | `PRODUCT_DECISION_REQUIRED` | Explicit human-decision flag. |
| 4 | `status == "approval_needed"` OR `status == "unclear"` | `PRODUCT_DECISION_REQUIRED` | Product ambiguity. |
| 5 | `defect_category == "unclear_requirement"` | `PRODUCT_DECISION_REQUIRED` | Can't classify without clear requirements. |
| 6 | `status == "fail"` AND `expected_observable_behavior` is blank | `NEEDS_EXPECTED_BEHAVIOR` | Failure reported but no expected behavior to compare against. Cannot become a bugfix candidate. |
| 7 | `status == "fail"` AND `evidence_level == "INFERRED"` | `PRODUCT_DECISION_REQUIRED` | Inferred evidence cannot confirm a bug. Demoted from candidate. |
| 8 | `status == "fail"` AND `actual_observed_behavior == "NOT_EXAMINED"` | `PRODUCT_DECISION_REQUIRED` | Code-only evidence: failure claimed but no runtime observation. Static evidence cannot confirm runtime failure. |
| 9 | `status == "fail"` AND `defect_category == "ux_defect"` | `UX_FIX_CANDIDATE` | UX defect with sufficient evidence and expected behavior. |
| 10 | `status == "fail"` AND `defect_category in ("functional_bug", "data_integrity", "integration", "security", "performance")` | `BUGFIX_CANDIDATE` | Functional defect with sufficient evidence and expected behavior. |
| 11 | `status == "fail"` AND `defect_category == "missing_feature"` | `SPEC_GAP_CANDIDATE` | Feature missing, not broken. |
| 12 | `status == "fail"` AND `defect_category in ("none", other)` | `PRODUCT_DECISION_REQUIRED` | Failure signal with unspecified category — do not drop silently. |
| 13 | `status == "blocked"` | `PRODUCT_DECISION_REQUIRED` | Blocked status conflates harness, dependency, and environment issues. No clean signal to distinguish — escalate for human triage. (CONFLICT-1 resolved) |
| 14 | `defect_category == "missing_feature"` AND `status != "fail"` AND `evidence_level != "INFERRED"` | `SPEC_GAP_CANDIDATE` | Spec gap identified outside failure path. Evidence gate applied: code-scan can evidence absence (a feature is observably missing from the codebase), but pure inference cannot. |
| 15 | `defect_category == "missing_feature"` AND `status != "fail"` AND `evidence_level == "INFERRED"` | `PRODUCT_DECISION_REQUIRED` | Inferred spec gap — insufficient evidence for candidate classification. |
| 16 | `status == "untested"` AND no failure signals | `NO_ACTION` | Pure inventory row. Nothing actionable yet. |
| 17 | Catch-all: any remaining row | `PRODUCT_DECISION_REQUIRED` | Row carries non-default metadata but doesn't match a specific classification. Escalate, never drop silently. |

**Invariant**: `NO_ACTION` is reachable only via rule 16 (fully inert rows). Any row carrying non-default
defect_category, severity, fix_status, test_status, or actual_observed_behavior that does not match a
specific classification rule is escalated to `PRODUCT_DECISION_REQUIRED`, never silently dropped.

### "No failure signals" definition (rule 15)

A row has no failure signals when ALL of:
- `defect_category == "none"`
- `severity == "none"`
- `fix_status == "not_started"`
- `test_status in ("NOT_TESTED", "NOT_EXAMINED")`
- `actual_observed_behavior == "NOT_EXAMINED"`

If ANY of these fields carries a non-default value, the row is not inert and rule 16 does not apply.
Non-inert rows that don't match rules 1-15 fall to the catch-all (rule 17) → `PRODUCT_DECISION_REQUIRED`.

### `status` vs `test_status` contradiction (rule 2)

Contradiction is defined as:
- `status == "fail"` AND `test_status == "PASS"`
- `status == "untested"` AND `test_status in ("PASS", "FAIL")`

These signal data integrity issues requiring human review.

### Evidence strength gate (rules 7-8)

Candidate classifications (`BUGFIX_CANDIDATE`, `UX_FIX_CANDIDATE`) require:
1. Non-blank `expected_observable_behavior` (rule 6 catches blank)
2. Evidence level stronger than `INFERRED` (rule 7 catches INFERRED)
3. Runtime observation exists: `actual_observed_behavior != "NOT_EXAMINED"` (rule 8 catches code-only)

This enforces: **a classification is not overclaim. Static/code-only evidence cannot confirm runtime failure.**

---

## CONFLICT-1: HARNESS_FIX_CANDIDATE Signal — RESOLVED

**Issue**: There is no `defect_category` value for harness/tooling issues. The ledger schema has no field
that distinguishes "blocked by test infrastructure" from "blocked by dependency" or "blocked by environment."

**Decision**: `status == "blocked"` → `PRODUCT_DECISION_REQUIRED` in Slice 2A.
`HARNESS_FIX_CANDIDATE` remains a valid reserved classification value for future use
when explicit harness evidence is available (e.g. a dedicated `blocked_reason` field
or a harness-specific `defect_category` value).

**Status**: Resolved. No remaining CONFLICTs.

---

## Output Schema

### `product-ledger-classification.json`

```json
{
  "schema_version": 1,
  "source_ledger_sha256": "<sha256 of input feature-ledger.json>",
  "classified_at": "<ISO 8601 timestamp>",
  "total_rows": 12,
  "summary": {
    "NO_ACTION": 8,
    "NEEDS_EXPECTED_BEHAVIOR": 2,
    "BUGFIX_CANDIDATE": 1,
    "BLOCKED_NO_EVIDENCE": 1
  },
  "classifications": [
    {
      "feature_id": "FL-auth-login-form-a1b2c3d4",
      "classification": "NO_ACTION",
      "reason": "untested inventory row, no failure signals"
    }
  ]
}
```

**Fields**:
- `schema_version`: integer, starts at 1
- `source_ledger_sha256`: links output to exact input version
- `classified_at`: ISO timestamp (volatile, control-plane only)
- `total_rows`: count for quick sanity check
- `summary`: counts per classification (for .md rendering)
- `classifications`: one entry per ledger row, preserving `feature_id` for stable cross-reference
- `classifications[].reason`: human-readable explanation of which rule matched

**Determinism**: For the same input ledger, the `classifications` list (minus `classified_at` and `source_ledger_sha256`)
must be identical across runs. Each classification rule produces a fixed `reason` string with no row-volatile content.
Tests verify both properties.

**Input validation**: The classifier calls `ledger.validate()` before classifying. Parseable-but-schema-invalid
ledgers (e.g. rows with invalid `evidence_level` values) produce an error and no output.
Only valid ledgers are classified.

### `product-ledger-classification.md`

Human-readable rendering of the classification. Grouped by classification value, sorted by feature_id within groups.
Includes summary counts and the source ledger hash.

### Write strategy

The classification output is **machine-derived, fully regenerable, and control-plane-owned**.
Unlike Slice 1's `safe_write` (which protects human-edited target artifacts with provenance guards),
the classification output uses plain overwrite. Rationale:
- It is not a target-owned artifact
- It is not human-edited (it is derived from the ledger)
- Re-running the classifier on the same input produces the same output
- Provenance guards would add complexity with no benefit for a machine-generated advisory artifact

---

## Proposed Files

| File | Role |
|---|---|
| `hldspec/ledger_classifier.py` | Classification logic, decision table, output schema, write functions |
| `scripts/classify_ledger.py` | CLI entry point: `python3 scripts/classify_ledger.py --target <path>` |
| `tests_v2/test_ledger_classifier.py` | Decision table tests, output format tests, boundary tests |

### Changes to existing files

| File | Change |
|---|---|
| `hldspec/artifact_contracts.py` | Register `product-ledger-classification` contract |

No other existing files are modified.

---

## Artifact Contract Registration

```python
"product-ledger-classification": ArtifactContract(
    artifact_name="product-ledger-classification",
    schema_version=1,
    producer="ledger_classifier / Product QA Loop Driver Slice 2A",
    consumers=[],  # Slice 2B will add itself
    required_fields=["schema_version", "source_ledger_sha256", "classifications"],
    optional_fields=["classified_at", "total_rows", "summary"],
    input_artifacts=[],
    input_specs=[],  # reads from target qa dir, not sync
    output_artifacts=[
        "product_qa_loop/product-ledger-classification.json",
        "product_qa_loop/product-ledger-classification.md",
    ],
    notes=(
        "Control-plane classification of target-owned feature ledger rows. "
        "A classification is NOT a work order and is NOT implementation approval. "
        "Does not modify the ledger, invoke SpecKit, or touch product code. "
        "Future Slice 2B (workorder generation) is the first consumer."
    ),
),
```

---

## Test Plan

### Decision table coverage (one test per rule)

| Test | Input row state | Expected classification |
|---|---|---|
| `test_empty_evidence_blocked` | evidence="" | BLOCKED_NO_EVIDENCE |
| `test_status_test_status_contradiction` | status=fail, test_status=PASS | PRODUCT_DECISION_REQUIRED |
| `test_approval_needed_bool` | approval_needed=True | PRODUCT_DECISION_REQUIRED |
| `test_status_approval_needed` | status=approval_needed | PRODUCT_DECISION_REQUIRED |
| `test_status_unclear` | status=unclear | PRODUCT_DECISION_REQUIRED |
| `test_unclear_requirement` | defect_category=unclear_requirement | PRODUCT_DECISION_REQUIRED |
| `test_fail_blank_expected_behavior` | status=fail, expected="" | NEEDS_EXPECTED_BEHAVIOR |
| `test_fail_inferred_evidence` | status=fail, evidence_level=INFERRED, expected="x" | PRODUCT_DECISION_REQUIRED |
| `test_fail_not_examined_actual` | status=fail, actual_observed=NOT_EXAMINED, expected="x" | PRODUCT_DECISION_REQUIRED |
| `test_fail_ux_defect` | status=fail, defect=ux_defect, expected="x", actual="y", evidence_level=OBSERVED | UX_FIX_CANDIDATE |
| `test_fail_functional_bug` | status=fail, defect=functional_bug, expected="x", actual="y", evidence_level=OBSERVED | BUGFIX_CANDIDATE |
| `test_fail_data_integrity` | status=fail, defect=data_integrity, expected="x", actual="y", evidence_level=REPRODUCED | BUGFIX_CANDIDATE |
| `test_fail_security` | status=fail, defect=security, expected="x", actual="y", evidence_level=OBSERVED | BUGFIX_CANDIDATE |
| `test_fail_performance` | status=fail, defect=performance, expected="x", actual="y", evidence_level=OBSERVED | BUGFIX_CANDIDATE |
| `test_fail_integration` | status=fail, defect=integration, expected="x", actual="y", evidence_level=REPRODUCED | BUGFIX_CANDIDATE |
| `test_fail_missing_feature` | status=fail, defect=missing_feature, expected="x", actual="y", evidence_level=OBSERVED | SPEC_GAP_CANDIDATE |
| `test_fail_none_category` | status=fail, defect=none, expected="x", actual="y", evidence_level=OBSERVED | PRODUCT_DECISION_REQUIRED |
| `test_blocked_status` | status=blocked | PRODUCT_DECISION_REQUIRED |
| `test_missing_feature_not_fail_observed` | status=untested, defect=missing_feature, evidence_level=OBSERVED | SPEC_GAP_CANDIDATE |
| `test_missing_feature_not_fail_inferred` | status=untested, defect=missing_feature, evidence_level=INFERRED | PRODUCT_DECISION_REQUIRED |
| `test_untested_no_signals` | status=untested, defect=none, all defaults | NO_ACTION |
| `test_catchall_escalates` | non-fail, non-blocked, non-default metadata (e.g. severity=major) | PRODUCT_DECISION_REQUIRED |
| `test_historical_evidence_reaches_candidate` | status=fail, defect=functional_bug, evidence_level=HISTORICAL, expected="x", actual="y" | BUGFIX_CANDIDATE |

### Negative / boundary tests

| Test | What it verifies |
|---|---|
| `test_blank_expected_never_becomes_bugfix` | No path from blank expected to BUGFIX/UX candidate |
| `test_inferred_never_becomes_candidate` | No path from INFERRED evidence to BUGFIX/UX candidate |
| `test_code_only_never_confirms_failure` | actual_observed=NOT_EXAMINED blocks candidate classification |
| `test_no_speckit_invocation` | Module has no SpecKit imports or invocation code |
| `test_no_ledger_modification` | Classifier does not write to target qa dir |
| `test_no_specify_writes` | No .specify/ writes |
| `test_classification_not_work_order` | Output has no work_order, task, or implementation fields |
| `test_stable_feature_id_preserved` | Output feature_ids match input feature_ids exactly |
| `test_harness_fix_never_assigned` | No rule in Slice 2A assigns HARNESS_FIX_CANDIDATE |
| `test_harness_fix_is_valid_value` | HARNESS_FIX_CANDIDATE is in VALID_CLASSIFICATIONS (reserved) |

### Output format tests

| Test | What it verifies |
|---|---|
| `test_deterministic_output` | Same input → same classifications list (ignoring volatile fields) |
| `test_json_roundtrip` | Output parses back correctly |
| `test_summary_counts_match` | Summary counts match actual classification distribution |
| `test_total_rows_matches` | total_rows matches input ledger row count |
| `test_source_hash_matches` | source_ledger_sha256 matches sha256 of input file |
| `test_md_output_generated` | .md file is produced alongside .json |
| `test_output_under_control_plane` | Output path is under control_sync/product_qa_loop/ |
| `test_plain_overwrite` | Re-running overwrites previous output (no provenance guard) |

### Input validation tests

| Test | What it verifies |
|---|---|
| `test_empty_ledger_produces_empty_classification` | 0 rows → 0 classifications, no crash |
| `test_invalid_ledger_errors_cleanly` | Malformed input → error, no partial output |
| `test_missing_ledger_errors_cleanly` | Missing file → error, no crash |
| `test_schema_invalid_rows_error` | Parseable but invalid ledger (e.g. bad evidence_level) → error before classifying |

### Determinism invariants

| Test | What it verifies |
|---|---|
| `test_reason_strings_are_static` | Each rule produces a fixed reason string with no row-volatile content |
| `test_no_action_only_from_inert_rows` | NO_ACTION is never assigned to rows with non-default failure metadata |

### CLI tests

| Test | What it verifies |
|---|---|
| `test_cli_writes_classification` | CLI produces both .json and .md under control plane |
| `test_cli_missing_target_exits_nonzero` | Bad --target → nonzero exit |
| `test_cli_missing_ledger_exits_nonzero` | No ledger in target → nonzero exit |

---

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| ~~CONFLICT-1~~: HARNESS_FIX_CANDIDATE has no clean signal | Resolved | `blocked` → `PRODUCT_DECISION_REQUIRED`; `HARNESS_FIX_CANDIDATE` reserved for future explicit evidence |
| Classification overclaim | High | Evidence strength gate (rules 7-8) demotes INFERRED/code-only to PRODUCT_DECISION_REQUIRED |
| Stale classification after ledger update | Low | source_ledger_sha256 tracks input version; consumer can compare |
| Future schema drift between ledger and classifier | Low | Classifier reads via FeatureLedger.load() / LedgerRow — single source |

---

## Out-of-scope observations (do not fix in Slice 2A)

1. `feature_ledger.py:275` comment says `OBSERVED > REPRODUCED` but code correctly ranks `REPRODUCED > OBSERVED`.
   Stale comment from Slice 1. Fix separately.

2. The `feature-ledger` artifact contract in `artifact_contracts.py` has `consumers: []`.
   Slice 2A should add itself as a consumer when registering its own contract.

---

## RunSkeptic Review

### Receipt

- **Source read**: `saffih/skeptic@main` (skeptic.md fetched via raw GitHub URL; commit SHA not captured)
- **Companion files read**: none required
- **Permission mode**: read-only (plan only, no implementation)
- **DONE statement**: Produce a classification plan with total decision table, output schema, test plan, and risk register. Stop before implementation.
- **Major steps run**: GATE, FUNDAMENTAL SCAN, MAP (all 6 Thinkers), STRUCTURAL CHECKS, CONFIDENCE, STABILIZE, EVIDENCE, DECIDE
- **Thinkers considered**: CH, OM, FE, PO, KT, SH

### Findings

**CH (Munger)**:
- `CH:IN` — Incentive to overclaim: classifier could promote INFERRED evidence to BUGFIX_CANDIDATE.
  **Mitigated**: Rules 7-8 demote INFERRED and code-only evidence to PRODUCT_DECISION_REQUIRED.
- `CH:SM` — Safety margin: classification is advisory, not executory. Sufficient margin.
- `CH:IV` — Worst outcome: misclassification leads to wrong work order in Slice 2B.
  **Mitigated**: Slice 2B has its own gate; classification is input, not approval.
- `CH:CR` — Constraint risk: most Slice 1 scanner rows will be NO_ACTION (untested, no enrichment).
  Not a bug — the classifier correctly reflects the ledger state.

**OM (Occam)**:
- `OM:UE` — Schema is minimal: feature_id + classification + reason per row. No speculative fields.
- `OM:OD` — 8 classifications map to 8 distinct downstream actions. None removable.
- `OM:CF` — Plain overwrite (no provenance guard) is justified for machine-derived control-plane output.

**FE (Feynman)**:
- `FE:WE` — Weak evidence axis: Slice 1 scanner sets evidence_level=OBSERVED but evidence is file-existence,
  not runtime behavior. Rules 7-8 prevent this from becoming a candidate classification.
  **ACTION**: Observation noted. No Slice 2A fix needed — the decision table handles it.
- `FE:ME` — Mechanism is clear: deterministic rules on row fields, priority-ordered, total.
- `FE:HL` — Hidden limit: classifier only sees what the ledger records. If ledger is un-enriched,
  everything is NO_ACTION. This is correct, not a bug.

**PO (Popper)**:
- `PO:SI` — Silent invalidation: `status=fail` + `defect_category=none` was a silent drop in earlier draft.
  **Fixed**: Rule 12 routes this to PRODUCT_DECISION_REQUIRED, not NO_ACTION.
- `PO:CO` — Tests include both "correctly classified as X" and "not misclassified as Y" (negative tests).
- `PO:CN` — No contradictions in final table. Priority ordering resolves all overlaps.

**KT (Kant)**:
- `KT:UA` — No provenance guard on classification output vs Slice 1's `safe_write` on ledger.
  **Justified**: Different ownership (control-plane vs target), different mutability (machine-derived vs human-edited).
  Not asymmetry — different invariants for different artifact types.

**SH (Saffi)**:
- `SH:OF` — Opposing forces: "classify now with available data" vs "wait for better evidence."
  **Resolution**: BLOCKED_NO_EVIDENCE and PRODUCT_DECISION_REQUIRED are the explicit "not enough data" answers.
  The classifier does not invent signals or wait — it classifies what's there and flags gaps.
- `SH:HC` — No hidden conflict. Classifier reads ledger fields; does not need SpecKit knowledge.
- SH finding on HARNESS_FIX_CANDIDATE: **CONFLICT** surfaced (CONFLICT-1). **Resolved**: `blocked` → `PRODUCT_DECISION_REQUIRED`; value reserved for future explicit evidence.

### Evidence levels

| Finding | Evidence |
|---|---|
| Overclaim risk (INFERRED→candidate) | OBSERVED: decision table code path analysis |
| HARNESS_FIX_CANDIDATE signal gap | OBSERVED: ledger schema has no harness-specific field |
| Silent drop of fail+none | OBSERVED: draft table analysis, fixed in final table |
| Stale comment in feature_ledger.py:275 | OBSERVED: code says REPRODUCED:3 > OBSERVED:2, comment says opposite |

### Decisions

| Finding | Decision | Rationale |
|---|---|---|
| Overclaim risk | FIX (in plan) | Rules 7-8 added to decision table |
| Silent drop of fail+none | FIX (in plan) | Rule 12 added |
| HARNESS_FIX_CANDIDATE signal | HANDLED | Resolved: `blocked` → `PRODUCT_DECISION_REQUIRED`; value reserved for future explicit evidence |
| Stale Slice 1 comment | Out of scope | Mention, don't fix |

### Verdict

**The plan is ready to implement.** CONFLICT-1 resolved: `blocked` → `PRODUCT_DECISION_REQUIRED`;
`HARNESS_FIX_CANDIDATE` reserved for future explicit harness evidence. No remaining CONFLICTs.

Design notes resolved during review:
- Rule 17 catch-all escalates to PRODUCT_DECISION_REQUIRED (never silently drops to NO_ACTION)
- Rule 14/15 apply evidence gate to SPEC_GAP_CANDIDATE consistently with other candidates
- HISTORICAL evidence is intentionally allowed to reach candidate status (only INFERRED is demoted)
- Input validation via `ledger.validate()` before classification
- Reason strings are static per matched rule (no row-volatile content)

---

## Recommended Implementation Prompt

> Implement Slice 2A per `docs/SLICE_2A_PLAN.md`.
>
> Files to create:
> - `hldspec/ledger_classifier.py` — classification logic per the decision table
> - `scripts/classify_ledger.py` — CLI: `python3 scripts/classify_ledger.py --target <path>`
> - `tests_v2/test_ledger_classifier.py` — all tests from the test plan
>
> Files to modify:
> - `hldspec/artifact_contracts.py` — register `product-ledger-classification` contract,
>   add `"ledger_classifier"` to `feature-ledger` consumers list
>
> Hard rules:
> - Do not modify the ledger
> - Do not invoke SpecKit
> - Do not create work orders
> - Do not write to the target
> - Do not add browser automation
> - Classification output goes to `<control_sync>/product_qa_loop/` only
> - Tests first (TDD): write test, verify it fails, implement, verify it passes
> - All tests in `tests_v2/test_ledger_classifier.py` must pass
> - `python3 -m unittest discover -s tests_v2 -v` must remain fully green
>
> CONFLICT-1 resolved: `blocked` → `PRODUCT_DECISION_REQUIRED`. `HARNESS_FIX_CANDIDATE` is a
> valid reserved value but no Slice 2A rule assigns it.
