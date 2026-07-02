"""Journey 0 dry-run proof harness."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hldspec.journey0_artifacts import (
    BrownfieldEvidencePack,
    EvidenceItem,
    EvidenceLabel,
    HldCodeSpecGapReport,
    HldDraftabilityVerdict,
    HldUpdatePlan,
    ProductDecisionRegister,
    ProductSurfaceMap,
    SpecInventory,
)
from hldspec.journey0_classifiers import build_journey0_conservative_artifacts
from hldspec.journey0_collectors import collect_journey0_observed_evidence
from hldspec.journey0_draftability import compute_journey0_draftability_verdict
from hldspec.journey0_hld_update_plan import build_journey0_hld_update_plan
from hldspec.journey0_product_surface import build_journey0_product_surface_map

_MARKER_FILE_NAME = "journey0_evidence.json"


@dataclass(frozen=True)
class FileSnapshotEntry:
    relative_path: str
    sha256: str


@dataclass(frozen=True)
class Journey0DryRunResult:
    evidence_pack: BrownfieldEvidencePack
    product_surface_map: ProductSurfaceMap
    spec_inventory: SpecInventory
    gap_report: HldCodeSpecGapReport
    decision_register: ProductDecisionRegister
    draftability_verdict: HldDraftabilityVerdict
    hld_update_plan: HldUpdatePlan
    before_snapshot: tuple[FileSnapshotEntry, ...]
    after_snapshot: tuple[FileSnapshotEntry, ...]

    @property
    def target_unchanged(self) -> bool:
        return self.before_snapshot == self.after_snapshot


def run_journey0_dry_run(
    *,
    target_root: Path,
    allowed_relative_paths: tuple[str, ...],
) -> Journey0DryRunResult:
    root = Path(target_root).resolve()
    allowed_paths = _resolve_allowed_paths(root, allowed_relative_paths)

    before_snapshot = _snapshot_allowed_paths(root, allowed_paths)
    collected_pack = _collect_allowed_evidence(allowed_paths)
    marker_pack = _collect_marker_evidence(root, allowed_paths)
    evidence_pack = BrownfieldEvidencePack(
        evidence=collected_pack.evidence + marker_pack.evidence
    )

    product_surface_map = build_journey0_product_surface_map(evidence_pack)
    spec_inventory, gap_report, decision_register = (
        build_journey0_conservative_artifacts(evidence_pack)
    )
    draftability_verdict = compute_journey0_draftability_verdict(
        evidence_pack=evidence_pack,
        product_surface_map=product_surface_map,
        gap_report=gap_report,
        decision_register=decision_register,
    )
    hld_update_plan = build_journey0_hld_update_plan(
        draftability_verdict=draftability_verdict,
        evidence_pack=evidence_pack,
        product_surface_map=product_surface_map,
        spec_inventory=spec_inventory,
        gap_report=gap_report,
        decision_register=decision_register,
    )
    after_snapshot = _snapshot_allowed_paths(root, allowed_paths)
    if before_snapshot != after_snapshot:
        raise RuntimeError("Journey 0 dry run changed the authorized fixture scope.")

    return Journey0DryRunResult(
        evidence_pack=evidence_pack,
        product_surface_map=product_surface_map,
        spec_inventory=spec_inventory,
        gap_report=gap_report,
        decision_register=decision_register,
        draftability_verdict=draftability_verdict,
        hld_update_plan=hld_update_plan,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
    )


def _resolve_allowed_paths(
    root: Path,
    allowed_relative_paths: tuple[str, ...],
) -> tuple[Path, ...]:
    if not allowed_relative_paths:
        raise ValueError("allowed_relative_paths must not be empty")
    if not root.exists():
        raise FileNotFoundError(root)

    resolved: list[Path] = []
    for relative_path in allowed_relative_paths:
        candidate = Path(relative_path)
        if candidate.is_absolute():
            raise ValueError("allowed_relative_paths must be relative")
        path = (root / candidate).resolve()
        if os.path.commonpath((str(root), str(path))) != str(root):
            raise ValueError("allowed_relative_paths must stay under target_root")
        if not path.exists():
            raise FileNotFoundError(path)
        resolved.append(path)
    return tuple(sorted(resolved, key=lambda path: path.relative_to(root).as_posix()))


def _collect_allowed_evidence(allowed_paths: tuple[Path, ...]) -> BrownfieldEvidencePack:
    evidence: list[EvidenceItem] = []
    for path in allowed_paths:
        evidence.extend(collect_journey0_observed_evidence(path).evidence)
    return BrownfieldEvidencePack(
        evidence=tuple(
            _renumber_collected_evidence(index, item)
            for index, item in enumerate(evidence, start=1)
        )
    )


def _renumber_collected_evidence(index: int, item: EvidenceItem) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=f"COLLECTED-{index:03d}",
        source_type=item.source_type,
        source_ref=item.source_ref,
        source_location=item.source_location,
        summary=item.summary,
        label=item.label,
        confidence=item.confidence,
        related_items=item.related_items,
    )


def _collect_marker_evidence(
    root: Path,
    allowed_paths: tuple[Path, ...],
) -> BrownfieldEvidencePack:
    evidence: list[EvidenceItem] = []
    for marker_file in _marker_files(allowed_paths):
        payload = json.loads(marker_file.read_text(encoding="utf-8"))
        for item in payload.get("evidence", ()):
            evidence.append(_evidence_from_marker(root, marker_file, item))
    return BrownfieldEvidencePack(evidence=tuple(evidence))


def _marker_files(allowed_paths: tuple[Path, ...]) -> tuple[Path, ...]:
    markers: list[Path] = []
    for path in allowed_paths:
        if path.is_file() and path.name == _MARKER_FILE_NAME:
            markers.append(path)
        if path.is_dir():
            marker = path / _MARKER_FILE_NAME
            if marker.exists():
                markers.append(marker)
    return tuple(sorted(set(markers), key=lambda path: path.as_posix()))


def _evidence_from_marker(
    root: Path,
    marker_file: Path,
    item: dict[str, Any],
) -> EvidenceItem:
    rel = marker_file.relative_to(root).as_posix()
    return EvidenceItem(
        evidence_id=item["evidence_id"],
        source_type=item["source_type"],
        source_ref=rel,
        source_location=f"{rel}:1",
        summary=item["summary"],
        label=EvidenceLabel(item["label"]),
        confidence=item.get("confidence", "high"),
        related_items=tuple(item.get("related_items", ())),
    )


def _snapshot_allowed_paths(
    root: Path,
    allowed_paths: tuple[Path, ...],
) -> tuple[FileSnapshotEntry, ...]:
    entries: list[FileSnapshotEntry] = []
    for path in allowed_paths:
        for file_path in _snapshot_files(path):
            rel = file_path.relative_to(root).as_posix()
            entries.append(
                FileSnapshotEntry(
                    relative_path=rel,
                    sha256=hashlib.sha256(file_path.read_bytes()).hexdigest(),
                )
            )
    return tuple(sorted(entries, key=lambda entry: entry.relative_path))


def _snapshot_files(path: Path) -> tuple[Path, ...]:
    if path.is_file():
        return (path,)
    files = (
        file_path
        for file_path in path.rglob("*")
        if file_path.is_file() and not file_path.is_symlink()
    )
    return tuple(sorted(files, key=lambda file_path: file_path.as_posix()))
