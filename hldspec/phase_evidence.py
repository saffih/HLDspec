"""Shared phase-artifact evidence classification.

This module keeps HLDspec's progress language honest: artifact presence is not
completion. A phase is DONE only when the artifact exists and machine-readable
evidence explicitly says the validation/report passed.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ARTIFACT_MISSING = "MISSING"
ARTIFACT_PRESENT = "PRESENT"

EVIDENCE_NONE = "NONE"
EVIDENCE_UNVERIFIED = "UNVERIFIED"
EVIDENCE_PASS = "PASS"
EVIDENCE_FAIL = "FAIL"
EVIDENCE_STALE = "STALE"

PHASE_NOT_STARTED = "NOT_STARTED"
PHASE_PRESENT_UNVERIFIED = "PRESENT_UNVERIFIED"
PHASE_DONE_VERIFIED = "DONE_VERIFIED"
PHASE_BLOCKED = "BLOCKED"
PHASE_STALE = "STALE"

SAFETY_PASS = "PASS"
SAFETY_ACTION = "ACTION"
SAFETY_BLOCKED = "BLOCKED"

PASSING_EVIDENCE_STATUSES = {"PASS", "PASSED", "OK", "DONE", "APPROVED"}
FAILING_EVIDENCE_STATUSES = {"FAIL", "FAILED", "ACTION", "CONFLICT", "BLOCKED", "REWORK_REQUIRED"}


@dataclass(frozen=True)
class PhaseEvidence:
    artifact_state: str
    evidence_state: str
    phase_state: str
    safety_status: str
    artifact_path: str
    evidence_paths: tuple[str, ...] = ()
    passing_evidence_paths: tuple[str, ...] = ()
    failing_evidence_paths: tuple[str, ...] = ()


def _nonempty(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def _json_status(path: Path) -> str:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    if not isinstance(data, dict):
        return ""
    return str(data.get("status", "")).upper()


def assess_phase_artifact(artifact: Path, evidence_candidates: list[Path], *, stale: bool = False) -> PhaseEvidence:
    """Assess one phase artifact using evidence-bound DONE semantics."""
    artifact = Path(artifact)
    if not _nonempty(artifact):
        return PhaseEvidence(
            artifact_state=ARTIFACT_MISSING,
            evidence_state=EVIDENCE_NONE,
            phase_state=PHASE_NOT_STARTED,
            safety_status=SAFETY_PASS,
            artifact_path=str(artifact),
        )

    evidence_paths = tuple(str(path) for path in evidence_candidates if path.is_file())
    if stale:
        return PhaseEvidence(
            artifact_state=ARTIFACT_PRESENT,
            evidence_state=EVIDENCE_STALE,
            phase_state=PHASE_STALE,
            safety_status=SAFETY_BLOCKED,
            artifact_path=str(artifact),
            evidence_paths=evidence_paths,
        )

    passing: list[str] = []
    failing: list[str] = []
    for path in evidence_candidates:
        if not path.is_file() or path.suffix != ".json":
            continue
        status = _json_status(path)
        if status in PASSING_EVIDENCE_STATUSES:
            passing.append(str(path))
        elif status in FAILING_EVIDENCE_STATUSES:
            failing.append(str(path))

    if failing:
        return PhaseEvidence(
            artifact_state=ARTIFACT_PRESENT,
            evidence_state=EVIDENCE_FAIL,
            phase_state=PHASE_BLOCKED,
            safety_status=SAFETY_BLOCKED,
            artifact_path=str(artifact),
            evidence_paths=evidence_paths,
            failing_evidence_paths=tuple(failing),
        )

    if passing:
        return PhaseEvidence(
            artifact_state=ARTIFACT_PRESENT,
            evidence_state=EVIDENCE_PASS,
            phase_state=PHASE_DONE_VERIFIED,
            safety_status=SAFETY_PASS,
            artifact_path=str(artifact),
            evidence_paths=evidence_paths,
            passing_evidence_paths=tuple(passing),
        )

    return PhaseEvidence(
        artifact_state=ARTIFACT_PRESENT,
        evidence_state=EVIDENCE_UNVERIFIED,
        phase_state=PHASE_PRESENT_UNVERIFIED,
        safety_status=SAFETY_ACTION,
        artifact_path=str(artifact),
        evidence_paths=evidence_paths,
    )
