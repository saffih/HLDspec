"""Target run-state location helpers.

HLDspec can keep controller/process artifacts outside a target repository and
leave only a small pointer in the target. This keeps product branch work and
HLDspec orchestration state distinguishable.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
POINTER_FILE = ".hldspec-run.json"
RUNS_ENV = "HLDSPEC_RUNS_DIR"
CONTROL_ARTIFACTS = (".hldspec", "prompts")


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._").lower()
    return slug or "target"


def default_runs_root() -> Path:
    override = os.environ.get(RUNS_ENV)
    if override:
        return Path(override).expanduser()
    state_home = os.environ.get("XDG_STATE_HOME")
    if state_home:
        return Path(state_home).expanduser() / "hldspec" / "runs"
    return Path.home() / ".local" / "state" / "hldspec" / "runs"


def run_id_for_target(target: Path, source_hash: str) -> str:
    target = target.expanduser().resolve()
    digest = hashlib.sha256(str(target).encode("utf-8")).hexdigest()[:12]
    source_short = source_hash[:12] if source_hash else "nosource"
    return f"{_slug(target.name)}-{digest}-{source_short}"


def external_run_root(target: Path, source_hash: str, *, runs_root: Path | None = None) -> Path:
    return (runs_root or default_runs_root()).expanduser() / run_id_for_target(target, source_hash)


def pointer_path(target: Path) -> Path:
    return target / POINTER_FILE


def write_pointer(
    target: Path,
    *,
    controller_root: Path,
    source: Path,
    source_hash: str,
    mode: str,
    agent: str,
    workflow_trigger: str,
    created_or_updated_at: str,
) -> Path:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "controller_root": str(controller_root.expanduser().resolve()),
        "target": str(target.expanduser().resolve()),
        "source": str(source.expanduser().resolve()),
        "source_sha256": source_hash,
        "mode": mode,
        "agent": agent,
        "workflow_trigger": workflow_trigger,
        "created_or_updated_at": created_or_updated_at,
        "ownership": {
            "hldspec_controller": "external",
            "target_pointer": POINTER_FILE,
            "speckit_workspace": ".specify/",
            "product_files": "target-owned",
        },
    }
    path = pointer_path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def load_pointer(target: Path) -> dict[str, Any]:
    path = pointer_path(target)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "schema_version": SCHEMA_VERSION,
            "invalid": True,
            "path": str(path),
            "warnings": [f"Invalid {POINTER_FILE}; remove it or rerun hldspec start."],
        }
    if not isinstance(data, dict):
        return {
            "schema_version": SCHEMA_VERSION,
            "invalid": True,
            "path": str(path),
            "warnings": [f"Invalid {POINTER_FILE}; expected a JSON object."],
        }
    data["path"] = str(path)
    return data


def controller_root_from_pointer(target: Path) -> Path | None:
    data = load_pointer(target)
    controller = data.get("controller_root")
    if not controller:
        return None
    return Path(str(controller)).expanduser()


def _remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def _mirror_path(src: Path, dst: Path) -> None:
    if src.is_dir():
        if dst.exists() and not dst.is_dir():
            _remove_path(dst)
        dst.mkdir(parents=True, exist_ok=True)
        src_names = {child.name for child in src.iterdir()}
        for child in src.iterdir():
            _mirror_path(child, dst / child.name)
        for child in list(dst.iterdir()):
            if child.name not in src_names:
                _remove_path(child)
        return

    if dst.exists() and dst.is_dir():
        _remove_path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_target_control_artifacts(
    target: Path,
    *,
    controller_root: Path,
) -> list[dict[str, str]]:
    """Copy HLDspec controller artifacts out of the target repository.

    This is intentionally copy-only. The target copy must remain present until
    the target pointer has been written, so an interrupted externalization never
    leaves the target with neither local control state nor a resolvable pointer.
    """
    copied: list[dict[str, str]] = []
    controller_root.mkdir(parents=True, exist_ok=True)
    for rel in CONTROL_ARTIFACTS:
        src = target / rel
        if not src.exists():
            continue
        dst = controller_root / rel
        _mirror_path(src, dst)
        copied.append({"rel": rel, "from": str(src), "to": str(dst)})
    return copied


def delete_target_control_artifacts(target: Path, copied: list[dict[str, str]]) -> list[dict[str, str]]:
    """Delete target-local control artifacts after copy + pointer are durable."""
    removed: list[dict[str, str]] = []
    for item in copied:
        rel = str(item.get("rel") or "")
        if rel not in CONTROL_ARTIFACTS:
            continue
        src = target / rel
        if not src.exists():
            continue
        _remove_path(src)
        removed.append(item)
    return removed


def externalize_target_control_artifacts(
    target: Path,
    *,
    controller_root: Path,
) -> list[dict[str, str]]:
    """Copy then delete HLDspec controller artifacts.

    Callers that need crash-safe externalization must write the target pointer
    between ``copy_target_control_artifacts`` and ``delete_target_control_artifacts``.
    This wrapper is kept for internal/debug compatibility only.
    """
    copied = copy_target_control_artifacts(target, controller_root=controller_root)
    return delete_target_control_artifacts(target, copied)


def expected_hldspec_target_paths() -> tuple[str, ...]:
    return (POINTER_FILE, ".hldspec/", "prompts/")
