"""TargetWorkspaceAdapter — centralises all HLDspec-managed workspace paths.

Two layouts are supported:

- "legacy": paths match the current machine conventions
    working_hld  = <root>/HLD.md
    raw_hld      = <root>/HLD.raw.md
    hldspec_dir  = <root>/.hldspec
    specify_dir  = <root>/.specify
    sync_dir     = <root>/firstrun/.specify/sync
    conversion_sync_dir = <root>/.specify/sync
    events_path  = <root>/.specify/sync/hldspec_event_log.jsonl
    firstrun_dir = <root>/firstrun

- "new": target-workspace layout (P0-003 target state)
    working_hld  = <root>/targetHLD/HLD.md
    raw_hld      = <root>/targetHLD/raw/HLD.raw.md
    hldspec_dir  = <root>/.hldspec
    specify_dir  = <root>/.specify
    sync_dir     = <root>/.hldspec/sync
    events_path  = <root>/.hldspec/events.jsonl
    firstrun_dir = <root>/.hldspec/tool-runs/firstrun

All machines should obtain paths from the adapter instead of assembling them
inline, so switching layouts only requires changing the adapter construction.
"""
from __future__ import annotations

from dataclasses import dataclass
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
        if self.layout == "new":
            return self.hldspec_dir / "tool-runs" / "firstrun"
        return self.target_root / "firstrun"

    @property
    def sync_dir(self) -> Path:
        if self.layout == "new":
            return self.hldspec_dir / "sync"
        return self.firstrun_dir / ".specify" / "sync"

    @property
    def conversion_sync_dir(self) -> Path:
        if self.layout == "new":
            return self.sync_dir
        return self.specify_dir / "sync"

    @property
    def events_path(self) -> Path:
        if self.layout == "new":
            return self.hldspec_dir / "events.jsonl"
        return self.specify_dir / "sync" / "hldspec_event_log.jsonl"

    # ------------------------------------------------------------------
    # Source package (single-HLD SpecKit source-package architecture)
    #
    # HLDspec authors the approved source package under .hldspec/ (control
    # plane). A derived, read-only mirror is materialised under .specify/source/
    # for the SpecKit runner. The canonical invariant "HLDspec never *authors*
    # into .specify/" holds: the mirror is generated, not authored.
    # ------------------------------------------------------------------

    @property
    def source_package_dir(self) -> Path:
        """HLDspec-owned, authoritative approved source package."""
        return self.hldspec_dir / "source_package"

    @property
    def specify_source_mirror_dir(self) -> Path:
        """Derived, read-only mirror of the source package for the runner."""
        return self.specify_dir / "source"

    @property
    def specify_memory_dir(self) -> Path:
        """SpecKit-owned constitution location (applied at the approval gate)."""
        return self.specify_dir / "memory"

    # ------------------------------------------------------------------
    # Convenience factory
    # ------------------------------------------------------------------

    @classmethod
    def from_workspace_str(cls, workspace: str, layout: str = "legacy") -> "TargetWorkspaceAdapter":
        return cls(target_root=Path(workspace), layout=layout)
