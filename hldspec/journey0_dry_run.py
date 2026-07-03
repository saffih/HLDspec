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
from hldspec.journey0_declared_evidence import (
    DeclaredProductSurfaceItem,
    build_declared_evidence,
)
from hldspec.journey0_draftability import compute_journey0_draftability_verdict
from hldspec.journey0_hld_update_plan import build_journey0_hld_update_plan
from hldspec.journey0_product_surface import build_journey0_product_surface_map

_MARKER_FILE_NAME = "journey0_evidence.json"


@dataclass(frozen=True)
class FileSnapshotEntry:
    relative_path: str
    sha256: str


@dataclass(frozen=True)
class TargetSnapshotProofRow:
    relative_path: str
    resolved_path: str
    source_kind: str
    before_sha256: str
    after_sha256: str
    bytes_changed: bool
    hash_source: str


@dataclass(frozen=True)
class Journey0DryRunResult:
    target_root: str
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


def build_target_no_mutation_proof_rows(
    *,
    target_root: Path,
    dry_run_result: Journey0DryRunResult,
) -> tuple[TargetSnapshotProofRow, ...]:
    root = Path(target_root).resolve()
    if dry_run_result.target_root != str(root):
        raise RuntimeError("Journey 0 snapshot proof target_root does not match run.")
    before = _snapshot_index(dry_run_result.before_snapshot, "before")
    after = _snapshot_index(dry_run_result.after_snapshot, "after")
    if before.keys() != after.keys():
        raise RuntimeError("Journey 0 snapshot proof paths changed.")

    rows: list[TargetSnapshotProofRow] = []
    for relative_path in sorted(before):
        resolved_path = _resolve_snapshot_relative_path(root, relative_path)
        current_sha256 = hashlib.sha256(resolved_path.read_bytes()).hexdigest()
        if current_sha256 != after[relative_path].sha256:
            raise RuntimeError(
                "Journey 0 snapshot proof does not match current target bytes."
            )
        rows.append(
            TargetSnapshotProofRow(
                relative_path=relative_path,
                resolved_path=str(resolved_path),
                source_kind="approved_target_file",
                before_sha256=before[relative_path].sha256,
                after_sha256=after[relative_path].sha256,
                bytes_changed=before[relative_path].sha256
                != after[relative_path].sha256,
                hash_source="approved_target_path",
            )
        )
    return tuple(rows)


def run_journey0_dry_run(
    *,
    target_root: Path,
    allowed_relative_paths: tuple[str, ...],
    declared_product_surface_evidence: tuple[DeclaredProductSurfaceItem, ...] = (),
) -> Journey0DryRunResult:
    root = Path(target_root).resolve()
    allowed_paths = _resolve_allowed_paths(root, allowed_relative_paths)

    before_snapshot = _snapshot_allowed_paths(root, allowed_paths)
    collected_pack = _collect_allowed_evidence(allowed_paths)
    marker_pack = _collect_marker_evidence(root, allowed_paths)
    declared_pack = build_declared_evidence(declared_product_surface_evidence)
    evidence_pack = BrownfieldEvidencePack(
        evidence=collected_pack.evidence + marker_pack.evidence + declared_pack.evidence
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
        target_root=str(root),
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


def _snapshot_index(
    snapshot: tuple[FileSnapshotEntry, ...],
    phase: str,
) -> dict[str, FileSnapshotEntry]:
    entries: dict[str, FileSnapshotEntry] = {}
    for entry in snapshot:
        if entry.relative_path in entries:
            raise RuntimeError(f"Journey 0 {phase} snapshot has duplicate paths.")
        entries[entry.relative_path] = entry
    return entries


def _resolve_snapshot_relative_path(root: Path, relative_path: str) -> Path:
    path = Path(relative_path)
    if path.is_absolute():
        raise ValueError("snapshot relative_path must be relative")
    resolved_path = (root / path).resolve()
    if os.path.commonpath((str(root), str(resolved_path))) != str(root):
        raise ValueError("snapshot relative_path must stay under target_root")
    if not resolved_path.is_file():
        raise FileNotFoundError(resolved_path)
    return resolved_path
