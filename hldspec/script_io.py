from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json_dict(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def write_json_dict(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def select_sync_dir(workspace: Path, markers: tuple[str, ...]) -> Path:
    """Marker-based control sync selection through the canonical resolver.

    Existing legacy `.specify/sync` / `firstrun/.specify/sync` state keeps
    winning via markers (explicit legacy_fallback); fresh state lands in the
    pointer-resolved canonical `.hldspec/sync`.
    """
    from hldspec import control_paths

    return control_paths.resolve_control_sync_dir(
        workspace, create=True, legacy_fallback=True, markers=markers
    )
