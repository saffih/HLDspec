"""Read-only Journey 0 collector for controlled filesystem fixtures.

This slice proves fixture-directory to Journey 0 artifact-contract conversion.
It is intentionally not a real repository scanner: it reads only a small
allowlist of known fixture-relative files, never writes, never shells out, and
does not inspect arbitrary projects.
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from hldspec import journey0_artifact_contracts as j0
from hldspec import journey0_draftability_gate as gate


ALLOWED_RELATIVE_FILES: tuple[str, ...] = (
    "README.md",
    "hld.md",
    "state.json",
    "specs/workflow.md",
    "specs/state.md",
    "src/app.py",
    "src/core.py",
)


@dataclass(frozen=True)
class FilesystemFixtureArtifacts:
    """Collected Journey 0 artifacts from a controlled fixture directory."""

    evidence_pack: dict[str, Any]
    product_decision_register: list[dict[str, Any]]
    gap_report: dict[str, Any]
    candidate_requirements: list[dict[str, Any]]
    open_questions: list[str]
    safety_authority_gaps: list[str]
    authority: dict[str, Any]
    files_read: list[str]
    ignored_files: list[str]

    def draftability_input(self) -> gate.DraftabilityInput:
        return gate.DraftabilityInput(
            evidence_pack=self.evidence_pack,
            gap_report=self.gap_report,
            product_decision_register=self.product_decision_register,
            open_questions=tuple(self.open_questions),
            candidate_requirements=tuple(self.candidate_requirements),
            safety_authority_gaps=tuple(self.safety_authority_gaps),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_pack": self.evidence_pack,
            "product_decision_register": self.product_decision_register,
            "gap_report": self.gap_report,
            "candidate_requirements": self.candidate_requirements,
            "open_questions": self.open_questions,
            "safety_authority_gaps": self.safety_authority_gaps,
            "authority": self.authority,
            "files_read": self.files_read,
            "ignored_files": self.ignored_files,
        }


def collect_filesystem_fixture_evidence(
    fixture_root: str | Path,
) -> FilesystemFixtureArtifacts:
    """Read a controlled fixture directory and produce Journey 0 artifacts."""

    root = _as_path(fixture_root)
    if not root.is_dir():
        raise j0.InvalidJourney0ArtifactError("filesystem fixture root is not a directory")
    root_real = root.resolve(strict=True)

    parsed = _ParsedFixture()
    files_read: list[str] = []

    for relative_name in ALLOWED_RELATIVE_FILES:
        fixture_file = root / relative_name
        if fixture_file.is_symlink():
            raise j0.InvalidJourney0ArtifactError("controlled fixture file is a symlink")
        if not fixture_file.exists():
            continue
        _validate_fixture_file(root_real, fixture_file)
        files_read.append(relative_name)
        if relative_name == "state.json":
            _parse_state_json(relative_name, fixture_file.read_text(encoding="utf-8"), parsed)
        else:
            _parse_marker_text(relative_name, fixture_file.read_text(encoding="utf-8"), parsed)

    evidence_pack = {
        "kind": j0.ARTIFACT_BROWNFIELD_EVIDENCE_PACK,
        "evidence": parsed.evidence,
    }
    j0.evidence_items(evidence_pack)
    j0.open_product_decisions(parsed.product_decisions)

    gap_report = {
        "kind": j0.ARTIFACT_HLD_GAP_REPORT,
        "repo_state_conflict": parsed.repo_state_conflict,
    }
    j0.validate_artifact(gap_report)

    return FilesystemFixtureArtifacts(
        evidence_pack=evidence_pack,
        product_decision_register=parsed.product_decisions,
        gap_report=gap_report,
        candidate_requirements=parsed.candidate_requirements,
        open_questions=parsed.open_questions,
        safety_authority_gaps=parsed.safety_authority_gaps,
        authority=j0.journey0_authority_profile(),
        files_read=files_read,
        ignored_files=_ignored_top_level_entries(root),
    )


def evaluate_filesystem_fixture(
    fixture_root: str | Path,
) -> gate.DraftabilityResult:
    """Collect controlled fixture artifacts and evaluate draftability."""

    artifacts = collect_filesystem_fixture_evidence(fixture_root)
    return gate.evaluate_hld_draftability(artifacts.draftability_input())


@dataclass
class _ParsedFixture:
    evidence: list[dict[str, str]]
    product_decisions: list[dict[str, str]]
    candidate_requirements: list[dict[str, str]]
    open_questions: list[str]
    safety_authority_gaps: list[str]
    repo_state_conflict: bool

    def __init__(self) -> None:
        self.evidence = []
        self.product_decisions = []
        self.candidate_requirements = []
        self.open_questions = []
        self.safety_authority_gaps = []
        self.repo_state_conflict = False


def _parse_marker_text(relative_name: str, content: str, parsed: _ParsedFixture) -> None:
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        _apply_marker(relative_name, line, parsed)


def _parse_state_json(relative_name: str, content: str, parsed: _ParsedFixture) -> None:
    if not content.strip():
        return
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise j0.InvalidJourney0ArtifactError(
            f"invalid controlled fixture state JSON: {exc.msg}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise j0.InvalidJourney0ArtifactError("controlled fixture state JSON is not an object")

    for item in payload.get("evidence", ()):
        if not isinstance(item, Mapping):
            raise j0.InvalidJourney0ArtifactError("state evidence item is not an object")
        label = j0.validate_evidence_label(item.get("label"))
        statement = str(item.get("statement", "")).strip()
        if not statement:
            raise j0.InvalidJourney0ArtifactError("state evidence item has no statement")
        parsed.evidence.append(
            {"label": label, "statement": statement, "source": relative_name}
        )

    for decision in payload.get("product_decisions", ()):
        if not isinstance(decision, Mapping):
            raise j0.InvalidJourney0ArtifactError("state decision item is not an object")
        parsed.product_decisions.append(
            {
                "id": str(decision.get("id", "")).strip(),
                "status": str(decision.get("status", "OPEN")).strip(),
                "question": str(decision.get("question", "")).strip(),
            }
        )

    for requirement in payload.get("candidate_requirements", ()):
        if not isinstance(requirement, Mapping):
            raise j0.InvalidJourney0ArtifactError("state requirement item is not an object")
        parsed.candidate_requirements.append(
            _requirement(
                str(requirement.get("id", "")).strip(),
                str(requirement.get("evidence_label", "")).strip(),
                str(requirement.get("statement", "")).strip(),
            )
        )

    for question in payload.get("open_questions", ()):
        parsed.open_questions.append(str(question))
    for gap in payload.get("safety_authority_gaps", ()):
        parsed.safety_authority_gaps.append(str(gap))
    parsed.repo_state_conflict = bool(
        parsed.repo_state_conflict or payload.get("repo_state_conflict")
    )


def _apply_marker(relative_name: str, line: str, parsed: _ParsedFixture) -> None:
    key, separator, value = line.partition(":")
    if not separator:
        return
    marker = key.strip()
    detail = value.strip()

    if marker in j0.VALID_EVIDENCE_LABELS:
        parsed.evidence.append(
            {
                "label": j0.validate_evidence_label(marker),
                "statement": detail,
                "source": relative_name,
            }
        )
    elif marker == "PRODUCT_DECISION":
        parsed.product_decisions.append(_decision(detail))
    elif marker == "REPO_STATE_CONFLICT":
        parsed.repo_state_conflict = _truthy(detail)
    elif marker == "OPEN_QUESTION":
        parsed.open_questions.append(detail)
    elif marker == "REQUIREMENT_UNKNOWN":
        parsed.candidate_requirements.append(
            _requirement(detail, j0.EVIDENCE_UNKNOWN, detail)
        )
    elif marker == "REQUIREMENT_OBSERVED":
        parsed.candidate_requirements.append(
            _requirement(detail, j0.EVIDENCE_OBSERVED, detail)
        )
    elif marker == "SAFETY_AUTHORITY_GAP":
        parsed.safety_authority_gaps.append(detail)


def _decision(detail: str) -> dict[str, str]:
    decision_id = detail or "PRODUCT_DECISION_REQUIRED"
    return {
        "id": decision_id,
        "status": "PRODUCT_DECISION_REQUIRED",
        "question": detail,
    }


def _requirement(requirement_id: str, evidence_label: str, statement: str) -> dict[str, str]:
    label = j0.validate_evidence_label(evidence_label)
    if not requirement_id:
        raise j0.InvalidJourney0ArtifactError("fixture requirement has no id")
    return {
        "id": requirement_id,
        "evidence_label": label,
        "statement": statement,
    }


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _as_path(value: str | Path) -> Path:
    return getattr(pathlib, "Path")(value)


def _validate_fixture_file(root_real: Path, fixture_file: Path) -> None:
    if fixture_file.is_symlink():
        raise j0.InvalidJourney0ArtifactError("controlled fixture file is a symlink")
    if not fixture_file.is_file():
        raise j0.InvalidJourney0ArtifactError("controlled fixture entry is not a file")
    try:
        fixture_file.resolve(strict=True).relative_to(root_real)
    except ValueError as exc:
        raise j0.InvalidJourney0ArtifactError(
            "controlled fixture file resolves outside fixture root"
        ) from exc


def _ignored_top_level_entries(root: Path) -> list[str]:
    allowed_top_level = {name.split("/", 1)[0] for name in ALLOWED_RELATIVE_FILES}
    ignored: list[str] = []
    for child in root.iterdir():
        if child.name not in allowed_top_level:
            ignored.append(child.name)
    return sorted(ignored)
