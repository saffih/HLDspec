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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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


def externalize_target_control_artifacts(
    target: Path,
    *,
    controller_root: Path,
) -> list[dict[str, str]]:
    """Move HLDspec controller artifacts out of the target repository."""
    moved: list[dict[str, str]] = []
    controller_root.mkdir(parents=True, exist_ok=True)
    for rel in (".hldspec", "prompts"):
        src = target / rel
        if not src.exists():
            continue
        dst = controller_root / rel
        if dst.exists():
            if dst.is_dir():
                shutil.rmtree(dst)
            else:
                dst.unlink()
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        moved.append({"from": str(src), "to": str(dst)})
    return moved


def expected_hldspec_target_paths() -> tuple[str, ...]:
    return (POINTER_FILE, ".hldspec/", "prompts/")
