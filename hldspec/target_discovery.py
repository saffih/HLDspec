"""Read-only target discovery for existing-sensitive greenfield work."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from . import hld_source_package as hsp
from . import phase_evidence as pe
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

# Ledger safety dimension, orthogonal to lifecycle overall_status.
SAFETY_PASS = "PASS"
SAFETY_ACTION = "ACTION"
SAFETY_BLOCKED = "BLOCKED"
UNSAFE_SAFETY = frozenset({SAFETY_ACTION, SAFETY_BLOCKED})

# Source-package target/source binding states (invariant B). Only BOUND_MATCH
# lets the package itself count as trusted lineage; a positively wrong binding
# (mismatch/invalid) distrusts the whole target's control state, fail closed.
BINDING_BOUND_MATCH = "BOUND_MATCH"
BINDING_BOUND_MISMATCH = "BOUND_MISMATCH"
BINDING_UNBOUND_LEGACY = "UNBOUND_LEGACY"
BINDING_MISSING = "MISSING_BINDING"
BINDING_INVALID = "INVALID_BINDING"
SUSPECT_BINDING_STATES = frozenset({BINDING_BOUND_MISMATCH, BINDING_INVALID})

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
# A manifest must be one of these (a loadable, non-empty JSON object) for the
# source package to count as trusted lineage. A bare directory, a stray
# markdown file, or an unreadable JSON must never be trusted.
SOURCE_PACKAGE_MANIFESTS = (
    "source_package.json",
    "session_plan.json",
    "source_manifest.json",
)
# Relative to the resolved .hldspec dir (controller root in external mode).
IMPLEMENTATION_LINEAGE_MARKERS = (
    "sync/implementation_lineage.json",
    "sync/implementation_slice_report.json",
    "sync/slice_completion_report.json",
    "speckit_implementation_approval.json",
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


def _source_package_binding(target: Path, source_package_dir: Path) -> dict[str, Any]:
    """Classify the package's target/source binding against this target.

    States: BOUND_MATCH (binding present and matches), BOUND_MISMATCH (names a
    different target, or a different source than the run pointer records),
    INVALID_BINDING (unreadable metadata, partial or type-broken binding, or a
    target_path_sha256 that does not hash the recorded target_path),
    UNBOUND_LEGACY (metadata present, binding fields absent), MISSING_BINDING
    (no source_package.json at all).
    """
    path = source_package_dir / hsp.SOURCE_PACKAGE_FILE
    result: dict[str, Any] = {
        "state": BINDING_MISSING,
        "path": str(path),
        "mismatch_reason": None,
        "recorded_target_path": None,
        "warnings": [],
    }

    def invalid(reason: str) -> dict[str, Any]:
        result["state"] = BINDING_INVALID
        result["mismatch_reason"] = reason
        return result

    if not path.is_file():
        result["warnings"].append(f"Source package has no {hsp.SOURCE_PACKAGE_FILE}; it cannot prove target/source binding.")
        return result

    metadata = _load_json(path)
    if not metadata:
        return invalid(f"{hsp.SOURCE_PACKAGE_FILE} is not a readable non-empty JSON object")

    present = [name for name in hsp.BINDING_FIELDS if metadata.get(name) not in (None, "")]
    if not present:
        result["state"] = BINDING_UNBOUND_LEGACY
        result["warnings"].append(
            "Source package is legacy/unbound (no target/source binding fields); rebuild it with hldspec start to bind it. Unbound packages are not trusted lineage."
        )
        return result
    if len(present) != len(hsp.BINDING_FIELDS):
        missing = sorted(set(hsp.BINDING_FIELDS) - set(present))
        return invalid(f"binding fields are incomplete (missing: {', '.join(missing)})")

    recorded_target = metadata.get("target_path")
    recorded_hash = metadata.get("target_path_sha256")
    if not isinstance(recorded_target, str) or not isinstance(recorded_hash, str):
        return invalid("binding fields have wrong types")
    result["recorded_target_path"] = recorded_target
    if hsp.path_sha256(recorded_target) != recorded_hash:
        return invalid("target_path_sha256 does not match the recorded target_path")

    try:
        resolved_recorded = Path(recorded_target).expanduser().resolve()
    except OSError:
        return invalid(f"recorded target_path cannot be resolved: {recorded_target}")
    if resolved_recorded != target:
        result["state"] = BINDING_BOUND_MISMATCH
        result["mismatch_reason"] = f"package is bound to a different target: {recorded_target}"
        return result

    binding_source = metadata.get("source_sha256")
    pointer_source = run_state.load_pointer(target).get("source_sha256")
    if binding_source and pointer_source and str(binding_source) != str(pointer_source):
        result["state"] = BINDING_BOUND_MISMATCH
        result["mismatch_reason"] = "package source_sha256 does not match the run pointer's source HLD"
        return result

    result["state"] = BINDING_BOUND_MATCH
    return result


def _has_valid_source_package(target: Path) -> tuple[bool, list[dict[str, Any]], dict[str, Any] | None]:
    """Strict trusted-lineage check.

    Trusted only on real evidence, never on a bare directory:
    - a valid source-package manifest AND an hld_reference_map.json with at
      least one anchor AND a target/source binding that matches this target; or
    - a valid agent_session.json carrying both source and target fields.

    A `.hldspec-run.json` pointer is not evidence by itself: `_hldspec_dir`
    resolves through the pointer, so a pointer counts exactly when the
    controller root it names contains the valid state above.

    A package whose binding is BOUND_MISMATCH or INVALID_BINDING is positively
    foreign/tampered state: it distrusts the target even if an agent session
    would otherwise match (fail closed).
    """
    evidence: list[dict[str, Any]] = []
    trusted = False
    binding: dict[str, Any] | None = None

    source_package = _source_package_dir(target)
    if source_package.is_dir():
        binding = _source_package_binding(target, source_package)
        manifests = [
            source_package / name
            for name in SOURCE_PACKAGE_MANIFESTS
            if _load_json(source_package / name)
        ]
        ref_map = _load_json(source_package / "hld_reference_map.json")
        anchors = ref_map.get("anchors") if isinstance(ref_map.get("anchors"), dict) else None
        if manifests and anchors and binding["state"] == BINDING_BOUND_MATCH:
            trusted = True
            for path in manifests:
                evidence.append({"kind": "source_package_manifest", "path": str(path)})
            evidence.append(
                {
                    "kind": "hld_anchor_map",
                    "path": str(source_package / "hld_reference_map.json"),
                    "anchor_count": len(anchors),
                }
            )
            evidence.append(
                {
                    "kind": "source_package_binding",
                    "path": binding["path"],
                    "state": binding["state"],
                }
            )

    session_path = _hldspec_dir(target) / "agent_session.json"
    session = _load_json(session_path)
    session_source = session.get("source")
    session_target = session.get("target")
    # The session must be structurally what HLDspec writes (source is a dict
    # with a path) AND belong to this target — a session copied from another
    # target must never transfer trust.
    if isinstance(session_source, dict) and session_source.get("path") and session_target:
        try:
            belongs = Path(str(session_target)).expanduser().resolve() == target
        except OSError:
            belongs = False
        if belongs:
            trusted = True
            evidence.append({"kind": "agent_session", "path": str(session_path)})

    if binding is not None and binding["state"] in SUSPECT_BINDING_STATES:
        trusted = False

    if trusted:
        controller = _controller_root(target)
        if controller is not None:
            evidence.append(
                {
                    "kind": "hldspec_run_pointer",
                    "path": str(target / run_state.POINTER_FILE),
                    "controller_root": str(controller),
                }
            )
    return trusted, evidence, binding


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
            phase_evidence = pe.assess_phase_artifact(
                artifact,
                _validation_candidates(target, spec_dir, phase, artifact_name),
                stale=_artifact_is_stale(target, artifact) if _is_nonempty(artifact) else False,
            )
            exists = phase_evidence.artifact_state == pe.ARTIFACT_PRESENT
            if phase_evidence.phase_state == pe.PHASE_NOT_STARTED:
                status = PHASE_NOT_STARTED
            elif phase_evidence.phase_state == pe.PHASE_STALE:
                status = PHASE_STALE
                blockers.append(f"Stale phase artifact: {artifact}")
            elif phase_evidence.phase_state == pe.PHASE_BLOCKED:
                status = PHASE_BLOCKED
                failing = phase_evidence.failing_evidence_paths[0] if phase_evidence.failing_evidence_paths else str(artifact)
                blockers.append(f"Phase validation evidence reports a failing status: {failing}")
            elif phase_evidence.phase_state == pe.PHASE_DONE_VERIFIED:
                status = PHASE_DONE
            else:
                status = PHASE_UNVERIFIED
                blockers.append(f"Unverified phase artifact lacks passing HLDspec validation/report evidence: {artifact}")
            summary[status] += 1
            entries.append(
                {
                    "spec": spec_dir.name,
                    "phase": phase,
                    "artifact": str(artifact),
                    "artifact_exists": exists,
                    "artifact_state": phase_evidence.artifact_state,
                    "evidence_state": phase_evidence.evidence_state,
                    "phase_state": phase_evidence.phase_state,
                    "safety_status": phase_evidence.safety_status,
                    "status": status,
                    "trusted_evidence": list(phase_evidence.evidence_paths),
                }
            )

    # overall_status is lifecycle/progress only. Safety lives in
    # safety_status so an UNVERIFIED/STALE artifact can never hide behind an
    # "ACTIVE"-looking ledger.
    existing = [entry for entry in entries if entry["artifact_exists"]]
    if not existing:
        overall = PHASE_NOT_STARTED
    elif all(entry["status"] == PHASE_DONE for entry in existing):
        overall = PHASE_DONE
    else:
        overall = PHASE_ACTIVE

    statuses = {entry["status"] for entry in entries}
    if statuses & {PHASE_STALE, PHASE_BLOCKED}:
        safety = SAFETY_BLOCKED
    elif PHASE_UNVERIFIED in statuses:
        safety = SAFETY_ACTION
    else:
        safety = SAFETY_PASS

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "target": str(target),
        "overall_status": overall,
        "safety_status": safety,
        "summary": summary,
        "entries": entries,
        "blockers": sorted(dict.fromkeys(blockers)),
    }


def _has_implementation_lineage(target: Path) -> tuple[bool, list[dict[str, Any]]]:
    evidence: list[dict[str, Any]] = []
    # Resolve through the controller pointer so external-mode implementation
    # lineage is found in the controller root, not only target-local .hldspec.
    hldspec_dir = _hldspec_dir(target)
    for rel in IMPLEMENTATION_LINEAGE_MARKERS:
        path = hldspec_dir / rel
        if path.is_file():
            evidence.append({"kind": "implementation_lineage", "path": str(path)})
    return bool(evidence), evidence


def build_target_discovery(target: Path) -> dict[str, Any]:
    target = Path(target).expanduser().resolve()
    lineage_ok, lineage_evidence, package_binding = _has_valid_source_package(target)
    implementation_ok, implementation_evidence = _has_implementation_lineage(target)
    phase_ledger = build_phase_ledger(target)
    has_specs = bool(_spec_dirs(target))
    has_memory = _has_real_speckit_memory(target)
    existing_payload = _target_payload_paths(target)
    blockers: list[str] = []
    warnings: list[str] = []

    binding_state = package_binding["state"] if package_binding else None
    if package_binding:
        warnings.extend(str(item) for item in package_binding.get("warnings", []))
    if binding_state in SUSPECT_BINDING_STATES:
        blockers.append(
            f"Source package binding is {binding_state}: {package_binding.get('mismatch_reason')}. "
            "A copied or tampered source package must not transfer trust."
        )

    if (not target.exists() or _target_is_empty_or_control_only(target)) and not lineage_ok:
        classification = CLASS_NEW_GREENFIELD
        if binding_state in SUSPECT_BINDING_STATES:
            next_safe_action = "Stop. Remove or rebuild the mismatched source package with hldspec start for this target; copied packages are not trusted."
        elif binding_state in {BINDING_UNBOUND_LEGACY, BINDING_MISSING}:
            next_safe_action = "Rebuild the source package with hldspec start to bind it to this target; legacy/unbound packages are not trusted lineage."
        else:
            next_safe_action = "Prepare the target through HLDspec start; no existing product state was detected."
    elif not lineage_ok:
        classification = CLASS_UNKNOWN_BROWNFIELD
        blockers.append("Existing target content has no trusted HLDspec lineage; arbitrary brownfield adoption is unsupported in this slice.")
        if binding_state in SUSPECT_BINDING_STATES:
            next_safe_action = "Stop. The source package is bound to a different target/source (copied or tampered); rebuild it in place with hldspec start for this target."
        elif binding_state in {BINDING_UNBOUND_LEGACY, BINDING_MISSING}:
            next_safe_action = "Stop. Rebuild the source package with hldspec start to bind it to this target; legacy/unbound packages are not trusted lineage."
        else:
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
    if phase_ledger["safety_status"] in UNSAFE_SAFETY:
        blockers.append(f"Phase ledger safety blocks continuation: {phase_ledger['safety_status']}")

    sync = _sync_dir(target)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "target": str(target),
        "classification": classification,
        "trusted_hldspec_lineage": lineage_ok,
        "source_package_binding": package_binding,
        "lineage_evidence": lineage_evidence + implementation_evidence,
        "existing_payload_paths": [str(path) for path in existing_payload],
        "warnings": warnings,
        "specify_memory_exists": has_memory,
        "spec_phase_artifacts_exist": has_specs,
        "phase_ledger_status": phase_ledger["overall_status"],
        "phase_ledger_safety": phase_ledger["safety_status"],
        "blockers": sorted(dict.fromkeys(blockers)),
        "next_safe_action": next_safe_action,
        "phase_ledger": phase_ledger,
        "report_paths": {
            "discovery_json": str(sync / DISCOVERY_JSON),
            "discovery_md": str(sync / DISCOVERY_MD),
            "ledger_json": str(sync / LEDGER_JSON),
            "ledger_md": str(sync / LEDGER_MD),
        },
    }


def render_phase_ledger_md(ledger: dict[str, Any]) -> str:
    lines = [
        "# HLDspec Phase Wake Ledger",
        "",
        f"STATUS: {ledger.get('overall_status', PHASE_NOT_STARTED)}",
        f"SAFETY: {ledger.get('safety_status', SAFETY_PASS)}",
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
    binding = report.get("source_package_binding") if isinstance(report.get("source_package_binding"), dict) else None
    binding_line = f"Source package binding: `{binding.get('state', BINDING_MISSING)}`" if binding else "Source package binding: `none`"
    lines = [
        "# HLDspec Target Discovery Report",
        "",
        f"Classification: `{report.get('classification', CLASS_UNKNOWN_BROWNFIELD)}`",
        f"Trusted HLDspec lineage: `{str(report.get('trusted_hldspec_lineage', False)).lower()}`",
        binding_line,
        f"Phase ledger status: `{report.get('phase_ledger_status', PHASE_NOT_STARTED)}`",
        f"Phase ledger safety: `{report.get('phase_ledger_safety', SAFETY_PASS)}`",
        f"Next safe action: {report.get('next_safe_action', '')}",
        "",
        "## Existing-Sensitive Rule",
        "",
        "- Known-origin HLDspec/SpecKit continuation is managed greenfield evolution.",
        "- Arbitrary brownfield adoption remains unsupported.",
        "- Discovery is read-only except for HLDspec control reports under the resolved `.hldspec/sync/`; it never creates a missing target.",
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
    if binding and (binding.get("mismatch_reason") or binding.get("recorded_target_path")):
        lines.extend(["", "## Source Package Binding", ""])
        lines.append(f"- state: `{binding.get('state', BINDING_MISSING)}`")
        lines.append(f"- metadata: {binding.get('path', '')}")
        if binding.get("recorded_target_path"):
            lines.append(f"- recorded target: {binding.get('recorded_target_path')}")
        if binding.get("mismatch_reason"):
            lines.append(f"- reason: {binding.get('mismatch_reason')}")
    warnings = report.get("warnings") if isinstance(report.get("warnings"), list) else []
    if warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in warnings)
    lines.extend(["", "## Blockers", ""])
    blockers = report.get("blockers") if isinstance(report.get("blockers"), list) else []
    lines.extend(f"- {item}" for item in blockers) if blockers else lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def write_discovery_reports(target: Path) -> dict[str, Any]:
    target = Path(target).expanduser().resolve()
    report = build_target_discovery(target)
    # Checking a missing target must stay read-only: never create the target
    # as a side effect of inspecting it.
    if not target.is_dir():
        report["reports_written"] = False
        return report
    # Resolve through the controller pointer: in external mode reports belong
    # next to the rest of the HLDspec control state, never target-local.
    sync = _sync_dir(target)
    sync.mkdir(parents=True, exist_ok=True)
    ledger = report["phase_ledger"]
    (sync / DISCOVERY_JSON).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (sync / DISCOVERY_MD).write_text(render_target_discovery_md(report), encoding="utf-8")
    (sync / LEDGER_JSON).write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (sync / LEDGER_MD).write_text(render_phase_ledger_md(ledger), encoding="utf-8")
    report["reports_written"] = True
    return report
