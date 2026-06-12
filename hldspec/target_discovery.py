"""Read-only target discovery for existing-sensitive greenfield work."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from . import run_state
from .spec_bundles import utc_now

SCHEMA_VERSION = 1

CLASS_NEW_GREENFIELD = "NEW_GREENFIELD"
CLASS_PREPARED_GREENFIELD = "PREPARED_GREENFIELD"
CLASS_INITIALIZED_GREENFIELD = "INITIALIZED_GREENFIELD"
CLASS_PHASED_GREENFIELD = "PHASED_GREENFIELD"
CLASS_EVOLVING_GREENFIELD = "EVOLVING_GREENFIELD"
CLASS_UNKNOWN_BROWNFIELD = "UNKNOWN_BROWNFIELD"

PHASE_NOT_STARTED = "NOT_STARTED"
PHASE_ACTIVE = "ACTIVE"
PHASE_DONE = "DONE"
PHASE_UNVERIFIED = "UNVERIFIED"
PHASE_STALE = "STALE"
PHASE_BLOCKED = "BLOCKED"

SYNC_REL = Path(".hldspec") / "sync"
DISCOVERY_JSON = "target_discovery_report.json"
DISCOVERY_MD = "target_discovery_report.md"
LEDGER_JSON = "phase_ledger.json"
LEDGER_MD = "phase_ledger.md"

CONTROL_NAMES = {
    ".git",
    ".gitignore",
    ".DS_Store",
    run_state.POINTER_FILE,
    ".hldspec",
    "prompts",
}
SOURCE_PACKAGE_MARKERS = (
    "source_package.json",
    "session_plan.json",
    "source_manifest.json",
    "hld_reference_map.json",
    "engineering_guidelines.md",
)
IMPLEMENTATION_LINEAGE_MARKERS = (
    ".hldspec/sync/implementation_lineage.json",
    ".hldspec/sync/implementation_slice_report.json",
    ".hldspec/sync/slice_completion_report.json",
    ".hldspec/speckit_implementation_approval.json",
)
PHASES: tuple[tuple[str, str], ...] = (
    ("specify", "spec.md"),
    ("plan", "plan.md"),
    ("tasks", "tasks.md"),
    ("analyze", "analysis.md"),
)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_nonempty(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def _target_payload_paths(target: Path) -> list[Path]:
    if not target.exists() or not target.is_dir():
        return []
    paths: list[Path] = []
    for child in target.iterdir():
        if child.name in CONTROL_NAMES:
            continue
        if child.name == "targetHLD":
            continue
        paths.append(child)
    return paths


def _target_is_empty_or_control_only(target: Path) -> bool:
    if not target.exists():
        return True
    if not target.is_dir():
        return False
    return not _target_payload_paths(target)


def _controller_root(target: Path) -> Path | None:
    return run_state.controller_root_from_pointer(target)


def _hldspec_dir(target: Path) -> Path:
    controller = _controller_root(target)
    return (controller / ".hldspec") if controller is not None else (target / ".hldspec")


def _sync_dir(target: Path) -> Path:
    return _hldspec_dir(target) / "sync"


def _source_package_dir(target: Path) -> Path:
    return _hldspec_dir(target) / "source_package"


def _has_valid_source_package(target: Path) -> tuple[bool, list[dict[str, Any]]]:
    evidence: list[dict[str, Any]] = []
    source_package = _source_package_dir(target)
    if source_package.is_dir():
        evidence.append({"kind": "source_package_dir", "path": str(source_package)})
        for marker in SOURCE_PACKAGE_MARKERS:
            path = source_package / marker
            if path.exists():
                evidence.append({"kind": "source_package_marker", "path": str(path)})
        ref_map = _load_json(source_package / "hld_reference_map.json")
        anchors = ref_map.get("anchors") if isinstance(ref_map.get("anchors"), dict) else None
        if anchors:
            evidence.append({"kind": "hld_anchor_map", "path": str(source_package / "hld_reference_map.json"), "anchor_count": len(anchors)})
    session_path = _hldspec_dir(target) / "agent_session.json"
    if session_path.is_file():
        session = _load_json(session_path)
        if session.get("source") or session.get("target"):
            evidence.append({"kind": "agent_session", "path": str(session_path)})
    pointer = run_state.load_pointer(target)
    if pointer.get("controller_root") and not pointer.get("invalid"):
        evidence.append({"kind": "hldspec_run_pointer", "path": str(target / run_state.POINTER_FILE), "controller_root": pointer.get("controller_root")})
    return bool(evidence), evidence


def _has_real_speckit_memory(target: Path) -> bool:
    return (target / ".specify" / "memory").is_dir()


def _spec_dirs(target: Path) -> list[Path]:
    specs = target / "specs"
    if not specs.is_dir():
        return []
    return sorted(path for path in specs.iterdir() if path.is_dir())


def _validation_candidates(target: Path, spec_dir: Path, phase: str, artifact_name: str) -> list[Path]:
    slug = spec_dir.name
    sync = _sync_dir(target)
    return [
        spec_dir / f"{phase}_validation.json",
        spec_dir / f"{phase}_validation.md",
        spec_dir / f"{phase}_report.json",
        spec_dir / f"{phase}_report.md",
        spec_dir / ".hldspec_validation.json",
        sync / f"{slug}_{phase}_validation.json",
        sync / f"{slug}_{phase}_validation.md",
        sync / f"{slug}_{phase}_report.json",
        sync / f"{slug}_{phase}_report.md",
        sync / "speckit_execution_assessment.json",
        sync / "speckit_execution_assessment.md",
        sync / "phase_validation.json",
        sync / "phase_validation.md",
    ]


def _phase_has_evidence(target: Path, spec_dir: Path, phase: str, artifact_name: str) -> tuple[bool, list[str]]:
    paths = [path for path in _validation_candidates(target, spec_dir, phase, artifact_name) if path.is_file()]
    return bool(paths), [str(path) for path in paths]


def _artifact_is_stale(target: Path, artifact: Path) -> bool:
    freshness = _load_json(_hldspec_dir(target) / "source_freshness.json")
    if freshness.get("blocking") or freshness.get("working_hld_differs_from_source"):
        return True
    artifact_hashes = freshness.get("artifact_hashes")
    if isinstance(artifact_hashes, dict) and artifact.is_file():
        recorded = artifact_hashes.get(str(artifact)) or artifact_hashes.get(artifact.name)
        if recorded and recorded != _sha256(artifact):
            return True
    return False


def build_phase_ledger(target: Path) -> dict[str, Any]:
    target = Path(target).expanduser().resolve()
    entries: list[dict[str, Any]] = []
    blockers: list[str] = []
    summary = {
        PHASE_DONE: 0,
        PHASE_ACTIVE: 0,
        PHASE_UNVERIFIED: 0,
        PHASE_STALE: 0,
        PHASE_BLOCKED: 0,
        PHASE_NOT_STARTED: 0,
    }

    for spec_dir in _spec_dirs(target):
        for phase, artifact_name in PHASES:
            artifact = spec_dir / artifact_name
            exists = _is_nonempty(artifact)
            evidence_ok, evidence_paths = _phase_has_evidence(target, spec_dir, phase, artifact_name) if exists else (False, [])
            stale = _artifact_is_stale(target, artifact) if exists else False
            if not exists:
                status = PHASE_NOT_STARTED
            elif stale:
                status = PHASE_STALE
                blockers.append(f"Stale phase artifact: {artifact}")
            elif evidence_ok:
                status = PHASE_DONE
            else:
                status = PHASE_UNVERIFIED
                blockers.append(f"Unverified phase artifact lacks HLDspec validation/report evidence: {artifact}")
            summary[status] += 1
            entries.append(
                {
                    "spec": spec_dir.name,
                    "phase": phase,
                    "artifact": str(artifact),
                    "artifact_exists": exists,
                    "status": status,
                    "trusted_evidence": evidence_paths,
                }
            )

    if any(entry["status"] in {PHASE_UNVERIFIED, PHASE_STALE, PHASE_BLOCKED} for entry in entries):
        overall = PHASE_BLOCKED if any(entry["status"] == PHASE_BLOCKED for entry in entries) else PHASE_ACTIVE
    elif any(entry["status"] == PHASE_DONE for entry in entries):
        overall = PHASE_DONE
    elif entries:
        overall = PHASE_ACTIVE
    else:
        overall = PHASE_NOT_STARTED

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "target": str(target),
        "overall_status": overall,
        "summary": summary,
        "entries": entries,
        "blockers": sorted(dict.fromkeys(blockers)),
    }


def _has_implementation_lineage(target: Path) -> tuple[bool, list[dict[str, Any]]]:
    evidence: list[dict[str, Any]] = []
    for rel in IMPLEMENTATION_LINEAGE_MARKERS:
        path = target / rel
        if path.is_file():
            evidence.append({"kind": "implementation_lineage", "path": str(path)})
    return bool(evidence), evidence


def build_target_discovery(target: Path) -> dict[str, Any]:
    target = Path(target).expanduser().resolve()
    lineage_ok, lineage_evidence = _has_valid_source_package(target)
    implementation_ok, implementation_evidence = _has_implementation_lineage(target)
    phase_ledger = build_phase_ledger(target)
    has_specs = bool(_spec_dirs(target))
    has_memory = _has_real_speckit_memory(target)
    existing_payload = _target_payload_paths(target)
    blockers: list[str] = []

    if (not target.exists() or _target_is_empty_or_control_only(target)) and not lineage_ok:
        classification = CLASS_NEW_GREENFIELD
        next_safe_action = "Prepare the target through HLDspec start; no existing product state was detected."
    elif not lineage_ok:
        classification = CLASS_UNKNOWN_BROWNFIELD
        blockers.append("Existing target content has no trusted HLDspec lineage; arbitrary brownfield adoption is unsupported in this slice.")
        next_safe_action = "Stop. Do not adopt automatically; use a future explicit brownfield adoption flow."
    elif implementation_ok:
        classification = CLASS_EVOLVING_GREENFIELD
        next_safe_action = "Reassess managed greenfield evolution from existing HLDspec lineage before issuing the next implementation-slice handoff."
    elif has_specs:
        classification = CLASS_PHASED_GREENFIELD
        next_safe_action = "Review the phase ledger and resolve UNVERIFIED or STALE artifacts before continuing."
    elif has_memory:
        classification = CLASS_INITIALIZED_GREENFIELD
        next_safe_action = "Use Build Loop ready/operator-state to validate readiness before any SpecKit phase starts."
    else:
        classification = CLASS_PREPARED_GREENFIELD
        next_safe_action = "Continue from the existing HLDspec source package; do not wipe/rebuild by default."

    if phase_ledger["blockers"]:
        blockers.extend(phase_ledger["blockers"])
    if phase_ledger["overall_status"] in {PHASE_STALE, PHASE_BLOCKED}:
        blockers.append(f"Phase ledger status blocks continuation: {phase_ledger['overall_status']}")

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "target": str(target),
        "classification": classification,
        "trusted_hldspec_lineage": lineage_ok,
        "lineage_evidence": lineage_evidence + implementation_evidence,
        "existing_payload_paths": [str(path) for path in existing_payload],
        "specify_memory_exists": has_memory,
        "spec_phase_artifacts_exist": has_specs,
        "phase_ledger_status": phase_ledger["overall_status"],
        "blockers": sorted(dict.fromkeys(blockers)),
        "next_safe_action": next_safe_action,
        "phase_ledger": phase_ledger,
    }


def render_phase_ledger_md(ledger: dict[str, Any]) -> str:
    lines = [
        "# HLDspec Phase Wake Ledger",
        "",
        f"STATUS: {ledger.get('overall_status', PHASE_NOT_STARTED)}",
        f"Target: {ledger.get('target', '')}",
        "",
        "## Summary",
        "",
    ]
    summary = ledger.get("summary") if isinstance(ledger.get("summary"), dict) else {}
    for key in (PHASE_DONE, PHASE_ACTIVE, PHASE_UNVERIFIED, PHASE_STALE, PHASE_BLOCKED, PHASE_NOT_STARTED):
        lines.append(f"- {key}: {summary.get(key, 0)}")
    lines.extend(["", "## Entries", ""])
    entries = ledger.get("entries") if isinstance(ledger.get("entries"), list) else []
    if entries:
        for entry in entries:
            lines.append(f"- `{entry.get('spec')}` `{entry.get('phase')}`: `{entry.get('status')}` ({entry.get('artifact')})")
    else:
        lines.append("- none")
    lines.extend(["", "## Blockers", ""])
    blockers = ledger.get("blockers") if isinstance(ledger.get("blockers"), list) else []
    lines.extend(f"- {item}" for item in blockers) if blockers else lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def render_target_discovery_md(report: dict[str, Any]) -> str:
    lines = [
        "# HLDspec Target Discovery Report",
        "",
        f"Classification: `{report.get('classification', CLASS_UNKNOWN_BROWNFIELD)}`",
        f"Trusted HLDspec lineage: `{str(report.get('trusted_hldspec_lineage', False)).lower()}`",
        f"Phase ledger status: `{report.get('phase_ledger_status', PHASE_NOT_STARTED)}`",
        f"Next safe action: {report.get('next_safe_action', '')}",
        "",
        "## Existing-Sensitive Rule",
        "",
        "- Known-origin HLDspec/SpecKit continuation is managed greenfield evolution.",
        "- Arbitrary brownfield adoption remains unsupported.",
        "- Discovery is read-only except for HLDspec control reports under `.hldspec/sync/`.",
        "",
        "## Lineage Evidence",
        "",
    ]
    evidence = report.get("lineage_evidence") if isinstance(report.get("lineage_evidence"), list) else []
    if evidence:
        for item in evidence:
            lines.append(f"- `{item.get('kind', 'evidence')}` {item.get('path', '')}")
    else:
        lines.append("- none")
    lines.extend(["", "## Blockers", ""])
    blockers = report.get("blockers") if isinstance(report.get("blockers"), list) else []
    lines.extend(f"- {item}" for item in blockers) if blockers else lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def write_discovery_reports(target: Path) -> dict[str, Any]:
    target = Path(target).expanduser().resolve()
    sync = target / SYNC_REL
    sync.mkdir(parents=True, exist_ok=True)
    report = build_target_discovery(target)
    ledger = report["phase_ledger"]
    (sync / DISCOVERY_JSON).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (sync / DISCOVERY_MD).write_text(render_target_discovery_md(report), encoding="utf-8")
    (sync / LEDGER_JSON).write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (sync / LEDGER_MD).write_text(render_phase_ledger_md(ledger), encoding="utf-8")
    return report
