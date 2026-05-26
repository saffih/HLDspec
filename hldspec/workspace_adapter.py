"""TargetWorkspaceAdapter — centralises all HLDspec-managed workspace paths.

Two layouts are supported:

- "legacy": paths match the current machine conventions
    working_hld  = <root>/HLD.md
    raw_hld      = <root>/HLD.raw.md
    hldspec_dir  = <root>/.hldspec
    specify_dir  = <root>/.specify
    sync_dir     = <root>/firstrun/.specify/sync
    events_path  = <root>/.specify/sync/hldspec_event_log.jsonl
    firstrun_dir = <root>/firstrun

- "new": target-workspace layout (P0-003 target state)
    working_hld  = <root>/targetHLD/HLD.md
    raw_hld      = <root>/targetHLD/raw/HLD.raw.md
    hldspec_dir  = <root>/.hldspec
    specify_dir  = <root>/.specify
    sync_dir     = <root>/.hldspec/sync
    events_path  = <root>/.hldspec/events.jsonl
    firstrun_dir = <root>/firstrun  (unchanged)

All machines should obtain paths from the adapter instead of assembling them
inline, so switching layouts only requires changing the adapter construction.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class TargetWorkspaceAdapter:
    target_root: Path
    layout: str = "legacy"  # "legacy" | "new"

    def __post_init__(self) -> None:
        if self.layout not in {"legacy", "new"}:
            raise ValueError(f"layout must be 'legacy' or 'new', got {self.layout!r}")

    # ------------------------------------------------------------------
    # Core paths
    # ------------------------------------------------------------------

    @property
    def working_hld(self) -> Path:
        if self.layout == "new":
            return self.target_root / "targetHLD" / "HLD.md"
        return self.target_root / "HLD.md"

    @property
    def raw_hld(self) -> Path:
        if self.layout == "new":
            return self.target_root / "targetHLD" / "raw" / "HLD.raw.md"
        return self.target_root / "HLD.raw.md"

    @property
    def hldspec_dir(self) -> Path:
        return self.target_root / ".hldspec"

    @property
    def specify_dir(self) -> Path:
        return self.target_root / ".specify"

    @property
    def firstrun_dir(self) -> Path:
        return self.target_root / "firstrun"

    @property
    def sync_dir(self) -> Path:
        if self.layout == "new":
            return self.hldspec_dir / "sync"
        return self.firstrun_dir / ".specify" / "sync"

    @property
    def events_path(self) -> Path:
        if self.layout == "new":
            return self.hldspec_dir / "events.jsonl"
        return self.specify_dir / "sync" / "hldspec_event_log.jsonl"

    # ------------------------------------------------------------------
    # Convenience factory
    # ------------------------------------------------------------------

    @classmethod
    def from_workspace_str(cls, workspace: str, layout: str = "legacy") -> "TargetWorkspaceAdapter":
        return cls(target_root=Path(workspace), layout=layout)
