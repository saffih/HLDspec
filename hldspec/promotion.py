"""Promotion status — the canonical vocabulary for all artifact and gate states."""
from __future__ import annotations
from enum import Enum


class PromotionStatus(str, Enum):
    PROPOSED         = "PROPOSED"          # Artifact exists but not yet reviewed
    REVIEW_REQUIRED  = "REVIEW_REQUIRED"   # Needs human or gate review before use
    REWORK_REQUIRED  = "REWORK_REQUIRED"   # Gate failed; must be rebuilt
    APPROVAL_READY   = "APPROVAL_READY"    # Gate passed; awaiting human approval
    APPROVED         = "APPROVED"          # Human approved; may proceed
    BLOCKED          = "BLOCKED"           # Cannot proceed; dependency or gate failure
    STALE            = "STALE"             # Inputs changed after this artifact was produced
    SUPERSEDED       = "SUPERSEDED"        # Replaced by a newer version

    @classmethod
    def terminal_states(cls) -> frozenset["PromotionStatus"]:
        return frozenset({cls.APPROVED, cls.SUPERSEDED})

    @classmethod
    def blocking_states(cls) -> frozenset["PromotionStatus"]:
        return frozenset({cls.REWORK_REQUIRED, cls.BLOCKED, cls.STALE})

    def can_promote_to_approved(self) -> bool:
        return self == PromotionStatus.APPROVAL_READY

    def is_blocking(self) -> bool:
        return self in self.blocking_states()


class DeprecationStatus(str, Enum):
    ACTIVE             = "ACTIVE"            # In use; maintained
    COMPATIBILITY_ONLY = "COMPATIBILITY_ONLY"# Kept for backward compat; no new uses
    DEPRECATED         = "DEPRECATED"        # Will be removed; migration required
    ARCHIVED           = "ARCHIVED"          # Moved to archive; not in active flow
    REMOVED            = "REMOVED"           # Deleted; references are errors

    def is_active_control_signal(self) -> bool:
        """Return True if this status allows a term/artifact to control active flow."""
        return self == DeprecationStatus.ACTIVE

    @classmethod
    def legacy_states(cls) -> frozenset["DeprecationStatus"]:
        return frozenset({cls.COMPATIBILITY_ONLY, cls.DEPRECATED, cls.ARCHIVED, cls.REMOVED})
