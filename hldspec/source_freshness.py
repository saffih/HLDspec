from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def managed_target(target: Path) -> bool:
    return (target / ".hldspec" / "agent_session.json").is_file() or (
        target / ".hldspec" / "source_package" / "session_plan.json"
    ).is_file()


def recorded_source_path(target: Path) -> Path | None:
    session_path = target / ".hldspec" / "agent_session.json"
    try:
        session = json.loads(session_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    source = session.get("source") if isinstance(session, dict) else None
    path = source.get("path") if isinstance(source, dict) else None
    if not path:
        return None
    return Path(str(path)).expanduser()


def build_source_freshness(target: Path, source: Path) -> dict[str, Any]:
    target = Path(target).expanduser().resolve()
    source = Path(source).expanduser().resolve()
    default_raw = target / "targetHLD" / "raw" / "HLD.raw.md"
    default_working = target / "targetHLD" / "HLD.md"
    legacy_working = target / "HLD.md"
    working = default_working if default_working.is_file() or not legacy_working.is_file() else legacy_working
    raw = default_raw if default_raw.is_file() or working != legacy_working else legacy_working
    warnings: list[str] = []

    if not source.is_file():
        warnings.append(f"Source HLD is missing or unreadable: {source}")
        source_hash = None
        source_text = None
    else:
        source_hash = sha256_file(source)
        source_text = source.read_text(encoding="utf-8")

    raw_hash = sha256_file(raw) if raw.is_file() else None
    working_hash = sha256_file(working) if working.is_file() else None
    if source_hash and raw_hash and raw_hash != source_hash:
        warnings.append("Raw HLD copy differs from the current source HLD.")
    if source_hash and working_hash and working_hash != source_hash:
        warnings.append(
            f"Source HLD content differs from the existing workspace HLD copy; conversion/update must reconcile {working} before derived artifacts are promoted."
        )
    if source_text is not None and not working.is_file():
        warnings.append(f"Working HLD copy is missing: {working}")

    state = "stale" if warnings else "fresh"
    return {
        "schema_version": SCHEMA_VERSION,
        "state": state,
        "blocking": state != "fresh",
        "source": str(source),
        "source_sha256": source_hash,
        "raw_copy": str(raw),
        "raw_copy_sha256": raw_hash,
        "working_copy": str(working),
        "working_copy_sha256": working_hash,
        "working_hld_existed": working.is_file(),
        "working_hld_differs_from_source": bool(source_hash and working_hash and working_hash != source_hash),
        "source_hld_modified": False,
        "warnings": warnings,
    }


def write_source_freshness(target: Path, source: Path) -> dict[str, Any]:
    report = build_source_freshness(target, source)
    path = Path(target) / ".hldspec" / "source_freshness.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def load_source_freshness(target: Path, *, recompute: bool = True) -> dict[str, Any]:
    target = Path(target).expanduser().resolve()
    path = target / ".hldspec" / "source_freshness.json"
    if not path.exists():
        if recompute:
            source = recorded_source_path(target)
            if source is not None:
                return write_source_freshness(target, source)
        managed = managed_target(target)
        return {
            "schema_version": SCHEMA_VERSION,
            "state": "absent" if managed else "not_managed",
            "blocking": managed,
            "path": str(path),
            "warnings": [f"Missing source freshness metadata: {path}"] if managed else [],
            "working_hld_differs_from_source": False,
            "source_hld_modified": False,
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "schema_version": SCHEMA_VERSION,
            "state": "invalid",
            "blocking": True,
            "path": str(path),
            "warnings": [f"Invalid source freshness metadata: {exc}"],
            "working_hld_differs_from_source": False,
            "source_hld_modified": False,
        }
    if recompute:
        source = recorded_source_path(target)
        if source is not None:
            return write_source_freshness(target, source)
    warnings = data.get("warnings", [])
    warning_list = [str(item) for item in warnings if str(item).strip()] if isinstance(warnings, list) else []
    state = str(data.get("state") or ("stale" if warning_list or data.get("working_hld_differs_from_source") else "fresh"))
    data["state"] = state
    data["blocking"] = bool(data.get("blocking", state != "fresh"))
    data["warnings"] = warning_list
    return data
