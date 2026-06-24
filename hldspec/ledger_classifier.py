"""Product QA feature-ledger row classifier (Slice 2A).

Deterministic, priority-ordered classification of feature-ledger rows.
Reads the target-owned ledger; writes classification output to control-plane
only. Does not modify the ledger, invoke SpecKit, create work orders, or
touch product code.

A classification is not a work order and is not implementation approval.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import feature_ledger as fl

SCHEMA_VERSION = 1

VALID_CLASSIFICATIONS = frozenset({
    "NO_ACTION",
    "NEEDS_EXPECTED_BEHAVIOR",
    "BUGFIX_CANDIDATE",
    "UX_FIX_CANDIDATE",
    "HARNESS_FIX_CANDIDATE",
    "SPEC_GAP_CANDIDATE",
    "PRODUCT_DECISION_REQUIRED",
    "BLOCKED_NO_EVIDENCE",
})

CLASSIFICATION_JSON = "product-ledger-classification.json"
CLASSIFICATION_MD = "product-ledger-classification.md"
REPORT_SUBDIR = fl.PRODUCT_QA_REPORT_SUBDIR

_BUGFIX_CATEGORIES = frozenset({
    "functional_bug", "data_integrity", "integration", "security", "performance",
})

_INERT_TEST_STATUSES = frozenset({"NOT_TESTED", "NOT_EXAMINED"})


def _is_contradiction(row: fl.LedgerRow) -> bool:
    if row.status == "fail" and row.test_status == "PASS":
        return True
    if row.status == "untested" and row.test_status in ("PASS", "FAIL"):
        return True
    return False


def _is_inert(row: fl.LedgerRow) -> bool:
    return (
        row.defect_category == "none"
        and row.severity == "none"
        and row.fix_status == "not_started"
        and row.test_status in _INERT_TEST_STATUSES
        and row.actual_observed_behavior == "NOT_EXAMINED"
    )


@dataclass
class RowClassification:
    feature_id: str
    classification: str
    reason: str


def classify_row(row: fl.LedgerRow) -> RowClassification:
    fid = row.feature_id

    # Rule 1
    if not row.evidence or not row.evidence.strip():
        return RowClassification(fid, "BLOCKED_NO_EVIDENCE", "no evidence provided")

    # Rule 2
    if _is_contradiction(row):
        return RowClassification(fid, "PRODUCT_DECISION_REQUIRED", "status and test_status contradict")

    # Rule 3
    if row.approval_needed:
        return RowClassification(fid, "PRODUCT_DECISION_REQUIRED", "explicit approval flag set")

    # Rule 4
    if row.status in ("approval_needed", "unclear"):
        return RowClassification(fid, "PRODUCT_DECISION_REQUIRED", f"status is {row.status}")

    # Rule 5
    if row.defect_category == "unclear_requirement":
        return RowClassification(fid, "PRODUCT_DECISION_REQUIRED", "unclear requirement")

    # Rules 6-12: fail branch
    if row.status == "fail":
        # Rule 6
        if not row.expected_observable_behavior or not row.expected_observable_behavior.strip():
            return RowClassification(fid, "NEEDS_EXPECTED_BEHAVIOR", "failure without expected behavior defined")

        # Rule 7
        if row.evidence_level == "INFERRED":
            return RowClassification(fid, "PRODUCT_DECISION_REQUIRED", "failure with inferred evidence only")

        # Rule 8
        if row.actual_observed_behavior == "NOT_EXAMINED":
            return RowClassification(fid, "PRODUCT_DECISION_REQUIRED", "failure without runtime observation")

        # Rule 9
        if row.defect_category == "ux_defect":
            return RowClassification(fid, "UX_FIX_CANDIDATE", "UX defect with verified evidence")

        # Rule 10
        if row.defect_category in _BUGFIX_CATEGORIES:
            return RowClassification(fid, "BUGFIX_CANDIDATE", f"{row.defect_category} with verified evidence")

        # Rule 11
        if row.defect_category == "missing_feature":
            return RowClassification(fid, "SPEC_GAP_CANDIDATE", "missing feature identified as failure")

        # Rule 12
        return RowClassification(fid, "PRODUCT_DECISION_REQUIRED", "failure with unspecified defect category")

    # Rule 13
    if row.status == "blocked":
        return RowClassification(fid, "PRODUCT_DECISION_REQUIRED", "blocked status requires triage")

    # Rules 14-15: missing_feature outside fail
    if row.defect_category == "missing_feature":
        if row.evidence_level != "INFERRED":
            return RowClassification(fid, "SPEC_GAP_CANDIDATE", "missing feature with non-inferred evidence")
        return RowClassification(fid, "PRODUCT_DECISION_REQUIRED", "missing feature with inferred evidence only")

    # Rule 16
    if row.status == "untested" and _is_inert(row):
        return RowClassification(fid, "NO_ACTION", "untested inventory row, no failure signals")

    # Rule 17
    return RowClassification(fid, "PRODUCT_DECISION_REQUIRED", "non-default metadata requires review")


def classify_ledger(ledger: fl.FeatureLedger) -> list[RowClassification]:
    return [classify_row(row) for row in ledger.rows]


@dataclass
class ClassificationResult:
    schema_version: int
    source_ledger_sha256: str
    classified_at: str
    total_rows: int
    summary: dict[str, int]
    classifications: list[dict[str, str]]


def build_result(
    ledger: fl.FeatureLedger,
    source_hash: str,
) -> ClassificationResult:
    classified = classify_ledger(ledger)
    counts: Counter[str] = Counter()
    entries = []
    for c in classified:
        counts[c.classification] += 1
        entries.append({
            "feature_id": c.feature_id,
            "classification": c.classification,
            "reason": c.reason,
        })
    return ClassificationResult(
        schema_version=SCHEMA_VERSION,
        source_ledger_sha256=source_hash,
        classified_at=datetime.now(timezone.utc).isoformat(),
        total_rows=len(ledger.rows),
        summary=dict(counts),
        classifications=entries,
    )


def result_to_dict(result: ClassificationResult) -> dict:
    return {
        "schema_version": result.schema_version,
        "source_ledger_sha256": result.source_ledger_sha256,
        "classified_at": result.classified_at,
        "total_rows": result.total_rows,
        "summary": result.summary,
        "classifications": result.classifications,
    }


def result_to_json(result: ClassificationResult) -> str:
    return json.dumps(result_to_dict(result), indent=2, sort_keys=False) + "\n"


def result_to_md(result: ClassificationResult) -> str:
    lines = [
        "# Product Ledger Classification Report",
        "",
        f"Source ledger SHA256: `{result.source_ledger_sha256}`",
        f"Classified at: {result.classified_at}",
        f"Total rows: {result.total_rows}",
        "",
        "## Summary",
        "",
    ]
    for cls_val in sorted(result.summary):
        lines.append(f"- **{cls_val}**: {result.summary[cls_val]}")
    lines.append("")

    grouped: dict[str, list[dict[str, str]]] = {}
    for entry in result.classifications:
        grouped.setdefault(entry["classification"], []).append(entry)

    for cls_val in sorted(grouped):
        lines.append(f"## {cls_val}")
        lines.append("")
        for entry in sorted(grouped[cls_val], key=lambda e: e["feature_id"]):
            lines.append(f"- `{entry['feature_id']}` — {entry['reason']}")
        lines.append("")

    return "\n".join(lines)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class ClassificationPaths:
    json_path: Path
    md_path: Path


def write_classification(
    result: ClassificationResult,
    control_sync_dir: Path,
) -> ClassificationPaths:
    out_dir = control_sync_dir / REPORT_SUBDIR
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / CLASSIFICATION_JSON
    md_path = out_dir / CLASSIFICATION_MD

    json_path.write_text(result_to_json(result), encoding="utf-8")
    md_path.write_text(result_to_md(result), encoding="utf-8")

    return ClassificationPaths(json_path=json_path, md_path=md_path)


def load_and_classify(
    qa_dir: Path,
    control_sync_dir: Path,
) -> tuple[ClassificationResult, ClassificationPaths]:
    ledger_json_path = qa_dir / fl.LEDGER_JSON
    if not ledger_json_path.is_file():
        raise FileNotFoundError(f"feature ledger not found: {ledger_json_path}")

    ledger = fl.FeatureLedger.load(qa_dir)
    errors = ledger.validate()
    if errors:
        raise ValueError(f"ledger validation failed: {'; '.join(errors)}")

    source_hash = _file_sha256(ledger_json_path)
    result = build_result(ledger, source_hash)
    paths = write_classification(result, control_sync_dir)
    return result, paths
