"""Canonical pointer-aware control-path resolution (invariant C).

Every HLDspec control read/write must resolve its sync dir through this module
so external-controller mode can never split state between the controller root
and target-local `.hldspec/sync` / `.specify/sync`.

Resolution:
- normal mode (no valid `.hldspec-run.json` pointer): `target/.hldspec[/sync]`
- external mode (pointer naming a controller root): `<controller>/.hldspec[/sync]`
- legacy `.specify/sync` / `firstrun/.specify/sync` are reachable only when the
  caller passes `legacy_fallback=True` AND a marker file proves state already
  lives there; no code path falls back to legacy silently.
- in external mode legacy fallback is ignored entirely: externalization copies
  the control state to the controller root, so a target-local legacy marker is
  by definition stale and must never split reads/writes away from the
  controller. (If a legacy-migration flow ever needs the old locations, it
  must add its own explicit opt-in rather than widening this default.)

Invalid pointer: `run_state.controller_root_from_pointer` returns None for a
missing or malformed pointer, so resolution falls back to target-local paths.
This deliberately preserves the pre-resolver semantics of
`target_discovery._hldspec_dir`: a broken pointer looks like a target with
no/foreign control state, which discovery already fails closed on (untrusted
lineage), rather than guessing at a controller location.
"""
from __future__ import annotations

from pathlib import Path

from . import run_state
from .workspace_adapter import TargetWorkspaceAdapter

LEGACY_SYNC_RELPATHS: tuple[str, ...] = (".specify/sync", "firstrun/.specify/sync")


def resolve_controller_root(target: Path) -> Path | None:
    return run_state.controller_root_from_pointer(Path(target))


def build_target_adapter(workspace: str | Path, layout: str = "legacy") -> TargetWorkspaceAdapter:
    """Construct a `TargetWorkspaceAdapter` with pointer-aware `controller_root`.

    Machines must use this instead of `TargetWorkspaceAdapter.from_workspace_str`,
    which hardcodes `controller_root=None` and reintroduces the writer/reader
    control-sync split this module exists to prevent.
    """
    target_root = Path(workspace)
    return TargetWorkspaceAdapter(
        target_root=target_root,
        layout=layout,
        controller_root=resolve_controller_root(target_root),
    )


def resolve_hldspec_dir(target: Path) -> Path:
    target = Path(target)
    controller = resolve_controller_root(target)
    return (controller / ".hldspec") if controller is not None else (target / ".hldspec")


def candidate_control_sync_dirs(target: Path, *, legacy_fallback: bool = False) -> tuple[Path, ...]:
    """Pointer-resolved canonical sync dir first; legacy read locations only on request.

    Legacy locations are offered only for non-external targets: with a valid
    controller pointer the controller sync is the single source of truth and
    stale target-local legacy markers must not win.
    """
    target = Path(target)
    controller = resolve_controller_root(target)
    hldspec_dir = (controller / ".hldspec") if controller is not None else (target / ".hldspec")
    candidates = [hldspec_dir / "sync"]
    if legacy_fallback and controller is None:
        candidates.extend(target / rel for rel in LEGACY_SYNC_RELPATHS)
    return tuple(candidates)


def resolve_control_sync_dir(
    target: Path,
    create: bool = False,
    legacy_fallback: bool = False,
    markers: tuple[str, ...] = (),
) -> Path:
    """Resolve the one control sync dir for this target.

    With `markers`, the first candidate already containing a marker wins, so
    existing state keeps being read where it lives — legacy dirs participate
    only when `legacy_fallback=True`. Without a marker hit the canonical dir
    is returned; `create=True` creates only that canonical dir, never a
    target-local dir in external mode and never a legacy dir.
    """
    candidates = candidate_control_sync_dirs(target, legacy_fallback=legacy_fallback)
    if markers:
        for sync in candidates:
            if any((sync / marker).exists() for marker in markers):
                return sync
    canonical = candidates[0]
    if create:
        canonical.mkdir(parents=True, exist_ok=True)
    return canonical
