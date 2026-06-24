"""Product QA feature ledger — observed behavior inventory.

Defines the canonical feature-ledger artifact: a persistent, row-stable record
of target-app features and their observed behavior status.

The ledger is a target/product QA artifact, not an HLD, spec, or SpecKit
artifact. It records what the app actually does vs what it should do.

Evidence levels reuse audit-project vocabulary (OBSERVED, REPRODUCED,
HISTORICAL, INFERRED) without modifying the audit prompt mechanism.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

VALID_STATUSES = frozenset({
    "untested",
    "fail",
    "blocked",
    "unclear",
    "approval_needed",
})

VALID_TEST_STATUSES = frozenset({
    "NOT_TESTED",
    "PASS",
    "FAIL",
    "BLOCKED",
    "NOT_EXAMINED",
})

VALID_RETEST_STATUSES = frozenset({
    "NOT_TESTED",
    "NOT_APPLICABLE",
    "RETEST_REQUIRED",
    "PASS",
    "FAIL",
    "BLOCKED",
})

VALID_EVIDENCE_LEVELS = frozenset({
    "OBSERVED",
    "REPRODUCED",
    "HISTORICAL",
    "INFERRED",
})

VALID_FIX_STATUSES = frozenset({
    "not_started",
    "in_progress",
    "fixed",
    "wont_fix",
    "deferred",
})

VALID_DEFECT_CATEGORIES = frozenset({
    "none",
    "functional_bug",
    "ux_defect",
    "missing_feature",
    "performance",
    "security",
    "data_integrity",
    "integration",
    "unclear_requirement",
})

VALID_SEVERITIES = frozenset({
    "blocker",
    "major",
    "minor",
    "cosmetic",
    "none",
})

LEDGER_JSON = "feature-ledger.json"
LEDGER_CSV = "feature-ledger.csv"
QA_RELPATH = "qa"

CSV_COLUMNS = [
    "feature_id",
    "stable_key",
    "area",
    "screen_or_component",
    "user_story",
    "preconditions",
    "inputs",
    "outputs",
    "expected_observable_behavior",
    "actual_observed_behavior",
    "actual_behavior_from_code",
    "test_steps",
    "status",
    "test_status",
    "retest_status",
    "defect_category",
    "severity",
    "evidence_level",
    "evidence",
    "fix_status",
    "approval_needed",
    "notes",
]


def resolve_product_qa_dir(target: Path) -> Path:
    return Path(target) / QA_RELPATH


def _stable_key(area: str, screen_or_component: str) -> str:
    return f"{area.strip().lower()}::{screen_or_component.strip().lower()}"


def _stable_feature_id(key: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", key).strip("-")
    short_hash = hashlib.sha256(key.encode()).hexdigest()[:8]
    return f"FL-{slug[:40]}-{short_hash}"


@dataclass
class LedgerRow:
    feature_id: str
    stable_key: str
    area: str
    screen_or_component: str
    user_story: str = ""
    preconditions: str = ""
    inputs: str = ""
    outputs: str = ""
    expected_observable_behavior: str = ""
    actual_observed_behavior: str = "NOT_EXAMINED"
    actual_behavior_from_code: str = ""
    test_steps: str = ""
    status: str = "untested"
    test_status: str = "NOT_TESTED"
    retest_status: str = "NOT_TESTED"
    defect_category: str = "none"
    severity: str = "none"
    evidence_level: str = "INFERRED"
    evidence: str = ""
    fix_status: str = "not_started"
    approval_needed: bool = False
    notes: str = ""

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.feature_id:
            errors.append("feature_id is required")
        if not self.area:
            errors.append("area is required")
        if not self.screen_or_component:
            errors.append("screen_or_component is required")
        if self.status not in VALID_STATUSES:
            errors.append(f"invalid status: {self.status}")
        if self.test_status not in VALID_TEST_STATUSES:
            errors.append(f"invalid test_status: {self.test_status}")
        if self.retest_status not in VALID_RETEST_STATUSES:
            errors.append(f"invalid retest_status: {self.retest_status}")
        if self.evidence_level not in VALID_EVIDENCE_LEVELS:
            errors.append(f"invalid evidence_level: {self.evidence_level}")
        if self.fix_status not in VALID_FIX_STATUSES:
            errors.append(f"invalid fix_status: {self.fix_status}")
        if self.defect_category not in VALID_DEFECT_CATEGORIES:
            errors.append(f"invalid defect_category: {self.defect_category}")
        if self.severity not in VALID_SEVERITIES:
            errors.append(f"invalid severity: {self.severity}")
        if self.evidence_level in VALID_EVIDENCE_LEVELS and not self.evidence:
            errors.append(f"evidence is required when evidence_level is {self.evidence_level}")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "LedgerRow":
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in d.items() if k in known}
        return cls(**filtered)


def make_row(area: str, screen_or_component: str, **kwargs: Any) -> LedgerRow:
    key = _stable_key(area, screen_or_component)
    fid = _stable_feature_id(key)
    return LedgerRow(feature_id=fid, stable_key=key, area=area, screen_or_component=screen_or_component, **kwargs)


@dataclass
class FeatureLedger:
    schema_version: int = SCHEMA_VERSION
    rows: list[LedgerRow] = field(default_factory=list)

    def add_row(self, row: LedgerRow) -> None:
        self.rows.append(row)

    def upsert_row(self, row: LedgerRow) -> None:
        """Add a row, or merge evidence into an existing row with the same id.

        Same stable key => same feature_id => one row. Re-discovery from another
        evidence source merges the new evidence instead of duplicating the row.
        """
        for existing in self.rows:
            if existing.feature_id == row.feature_id:
                _merge_evidence(existing, row)
                return
        self.rows.append(row)

    def validate(self) -> list[str]:
        errors: list[str] = []
        seen_ids: set[str] = set()
        for i, row in enumerate(self.rows):
            row_errors = row.validate()
            for e in row_errors:
                errors.append(f"row {i} ({row.feature_id}): {e}")
            if row.feature_id in seen_ids:
                errors.append(f"row {i}: duplicate feature_id {row.feature_id}")
            seen_ids.add(row.feature_id)
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "rows": [r.to_dict() for r in self.rows],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "FeatureLedger":
        return cls(
            schema_version=d.get("schema_version", SCHEMA_VERSION),
            rows=[LedgerRow.from_dict(r) for r in d.get("rows", [])],
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=False) + "\n"

    def to_csv(self) -> str:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in self.rows:
            writer.writerow(row.to_dict())
        return buf.getvalue()

    def write(self, qa_dir: Path) -> tuple[Path, Path]:
        qa_dir.mkdir(parents=True, exist_ok=True)
        json_path = qa_dir / LEDGER_JSON
        csv_path = qa_dir / LEDGER_CSV
        json_path.write_text(self.to_json(), encoding="utf-8")
        csv_path.write_text(self.to_csv(), encoding="utf-8")
        return json_path, csv_path

    @classmethod
    def load(cls, qa_dir: Path) -> "FeatureLedger":
        json_path = qa_dir / LEDGER_JSON
        if not json_path.is_file():
            return cls()
        data = json.loads(json_path.read_text(encoding="utf-8"))
        return cls.from_dict(data)


def _merge_evidence(existing: LedgerRow, incoming: LedgerRow) -> None:
    if incoming.evidence and incoming.evidence not in existing.evidence:
        if existing.evidence:
            existing.evidence = f"{existing.evidence}; {incoming.evidence}"
        else:
            existing.evidence = incoming.evidence
    # Strongest available evidence level wins (OBSERVED > REPRODUCED > HISTORICAL > INFERRED).
    rank = {"OBSERVED": 3, "REPRODUCED": 2, "HISTORICAL": 1, "INFERRED": 0}
    if rank.get(incoming.evidence_level, -1) > rank.get(existing.evidence_level, -1):
        existing.evidence_level = incoming.evidence_level


# --- Overwrite/conflict-safe write -------------------------------------------

@dataclass
class WriteResult:
    written: bool
    conflict: bool
    reason: str = ""


def _existing_is_compatible(qa_dir: Path) -> tuple[bool, str]:
    """Return (compatible, reason). A fresh dir is compatible."""
    json_path = qa_dir / LEDGER_JSON
    if not json_path.is_file():
        return True, ""
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        return False, "existing feature-ledger.json is not valid JSON (manual edit or corruption)"
    if not isinstance(data, dict):
        return False, "existing feature-ledger.json is not an object"
    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        return False, f"existing feature-ledger.json schema_version {version!r} != {SCHEMA_VERSION}"
    return True, ""


def safe_write(ledger: "FeatureLedger", qa_dir: Path) -> WriteResult:
    """Write the ledger unless an incompatible/manual file already exists.

    A compatible (current schema, valid JSON) existing ledger is a normal
    regeneration target and is overwritten. An unknown schema version or
    malformed file is treated as a potential manual edit: do not overwrite.
    """
    compatible, reason = _existing_is_compatible(qa_dir)
    if not compatible:
        return WriteResult(written=False, conflict=True, reason=reason)
    ledger.write(qa_dir)
    return WriteResult(written=True, conflict=False)


# --- Control-plane scan report -----------------------------------------------

PRODUCT_QA_REPORT_SUBDIR = "product_qa_loop"
SCAN_REPORT_JSON = "product-ledger-scan-report.json"
SCAN_REPORT_MD = "product-ledger-scan-report.md"


@dataclass
class ScanReportPaths:
    json_path: Path
    md_path: Path


def write_scan_report(control_sync_dir: Path, meta: dict[str, Any]) -> ScanReportPaths:
    """Write scanner metadata/report under the resolved control plane sync dir.

    Volatile data (timestamps, run ids, counts) belongs here, never in the
    per-row stable ledger content.
    """
    report_dir = control_sync_dir / PRODUCT_QA_REPORT_SUBDIR
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / SCAN_REPORT_JSON
    md_path = report_dir / SCAN_REPORT_MD

    json_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = ["# Product Ledger Scan Report", ""]
    for key in sorted(meta):
        lines.append(f"- **{key}**: {meta[key]}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return ScanReportPaths(json_path=json_path, md_path=md_path)


# --- Conservative code-only scanner ------------------------------------------

_ROUTE_DIR_HINTS = ("routes", "pages", "views", "screens")
_COMPONENT_EXTS = (".tsx", ".jsx", ".vue", ".svelte")
_SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", "__pycache__", "qa", ".hldspec", ".specify"}


def _looks_like_route(path: Path) -> bool:
    if path.suffix.lower() not in _COMPONENT_EXTS:
        return False
    return any(part.lower() in _ROUTE_DIR_HINTS for part in path.parts)


def _detect_inputs(text: str) -> str:
    hints = []
    if re.search(r"<form\b", text, re.IGNORECASE):
        hints.append("form")
    if re.search(r"<input\b", text, re.IGNORECASE):
        hints.append("input")
    if re.search(r"<button\b", text, re.IGNORECASE):
        hints.append("button")
    return ", ".join(hints)


def scan_target(target: Path) -> "FeatureLedger":
    """Read-only conservative scan: derive feature rows from routes/components.

    Never writes to the target. Every row carries evidence and a non-pass
    status. actual_observed_behavior stays NOT_EXAMINED (no runtime in Slice 1).
    """
    target = Path(target)
    ledger = FeatureLedger()

    candidates: list[Path] = []
    for path in target.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.relative_to(target).parts):
            continue
        if _looks_like_route(path):
            candidates.append(path)

    for path in sorted(candidates, key=lambda p: str(p.relative_to(target))):
        rel = path.relative_to(target)
        area = rel.parts[-2] if len(rel.parts) >= 2 else "root"
        component = path.stem
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            text = ""
        inputs = _detect_inputs(text)
        row = make_row(
            area,
            component,
            user_story=f"User interacts with the {component} {area} screen",
            inputs=inputs,
            actual_behavior_from_code=f"Route/component file at {rel}" + (f"; UI elements: {inputs}" if inputs else ""),
            status="untested",
            test_status="NOT_TESTED",
            retest_status="NOT_TESTED",
            evidence_level="OBSERVED",
            evidence=f"{rel}",
            notes="Conservative code-only inference; behavior not runtime-verified.",
        )
        ledger.upsert_row(row)

    return ledger
