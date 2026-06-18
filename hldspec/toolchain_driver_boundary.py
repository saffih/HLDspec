"""Toolchain Driver Boundary — zone classification for HLDspec-vs-tool-owned paths.

HLDspec operates toolchains (SpecKit today, future toolchains later); it does not
impersonate them. A Toolchain Driver may create/update HLDspec-owned artifacts,
read tool-owned artifacts as evidence, and write through a small number of
explicit adapter/mirror seams — it must never hand-edit a toolchain's generated or
governed files.

This module names those zones once so driver code (status reporting, helper
selection, future drivers) shares one definition instead of redefining
"tool-owned" per call site. See `docs/TOOLCHAIN_DRIVER_BOUNDARY.md` for the full
contract this module backs.

Existing enforcement this module does not replace:
`hldspec/refresh_target.py`'s `_classify_*` functions are the existing, already
-implemented per-file safety classification for the install/refresh step
(`OWNED_BY_HLDSPEC_SAFE_TO_UPDATE`, `EXISTS_BUT_UNOWNED_DO_NOT_TOUCH`, etc.),
including the narrow managed-block exception that lets refresh-target update
`.specify/memory/constitution.md` between explicit markers. That mechanism is not
refactored to use this module — same boundary, two call sites, both required to
agree on what "tool-owned" means. This module's `.specify/memory` classification
is deliberately the coarser default (read-only evidence, no write seam) for any
*new* driver code that has not implemented that specific managed-block protocol.
"""
from __future__ import annotations

from pathlib import Path

ZONE_HLDSPEC_OWNED = "HLDSPEC_OWNED"
ZONE_ADAPTER_MIRROR = "ADAPTER_MIRROR"
ZONE_READ_ONLY_EVIDENCE = "READ_ONLY_EVIDENCE"
ZONE_TOOL_OWNED_FORBIDDEN = "TOOL_OWNED_FORBIDDEN"
ZONE_AMBIGUOUS_ESCALATE = "AMBIGUOUS_ESCALATE"

VALID_ZONES: frozenset[str] = frozenset({
    ZONE_HLDSPEC_OWNED,
    ZONE_ADAPTER_MIRROR,
    ZONE_READ_ONLY_EVIDENCE,
    ZONE_TOOL_OWNED_FORBIDDEN,
    ZONE_AMBIGUOUS_ESCALATE,
})

# HLDspec-owned: the Toolchain Driver may create/update these freely. This is its
# own control state, never SpecKit's (or any toolchain's) territory.
HLDSPEC_OWNED_PREFIXES: tuple[str, ...] = (".hldspec",)

# Adapter/mirror: a narrow, explicit exception inside an otherwise tool-owned
# tree. HLDspec may write here ONLY as a generated, banner-stamped mirror — it is
# never authoritative (docs/JOURNEY2_PACKAGE_CONTRACT.md SS10).
ADAPTER_MIRROR_PREFIXES: tuple[str, ...] = (".specify/source",)

# Read-only evidence: the driver may read these to determine phase/status but
# must never write them. (`specs/<branch>/` phase artifacts and
# `.specify/memory/` are both named as required_target_evidence in
# docs/JOURNEY3_HELPER_CONTRACT.md §6.)
READ_ONLY_EVIDENCE_PREFIXES: tuple[str, ...] = (".specify/memory", "specs")

# Tool-owned forbidden: the rest of the toolchain's root. A Toolchain Driver must
# never hand-edit any of it.
TOOL_OWNED_ROOT_PREFIXES: tuple[str, ...] = (".specify",)


def _relative_posix(target: Path, path: Path) -> str | None:
    target = Path(target)
    path = Path(path)
    candidate = path if not path.is_absolute() else None
    if candidate is None:
        try:
            candidate = path.relative_to(target)
        except ValueError:
            return None
    return candidate.as_posix()


def _matches(rel_posix: str, prefixes: tuple[str, ...]) -> bool:
    return any(rel_posix == prefix or rel_posix.startswith(prefix + "/") for prefix in prefixes)


def classify_path(target: Path, path: Path) -> str:
    """Classify `path` (absolute under `target`, or already target-relative)
    into one ownership zone.

    Ambiguous-ownership escalation rule: a path that is not provably
    HLDspec-owned, an approved adapter/mirror seam, or a known read-only
    evidence/tool-owned root is treated as `ZONE_AMBIGUOUS_ESCALATE` — never
    assumed safe to write. An absolute path outside `target` is also escalated,
    since this module only classifies paths inside the target repo.
    """
    rel_posix = _relative_posix(target, path)
    if rel_posix is None:
        return ZONE_AMBIGUOUS_ESCALATE

    if _matches(rel_posix, HLDSPEC_OWNED_PREFIXES):
        return ZONE_HLDSPEC_OWNED
    if _matches(rel_posix, ADAPTER_MIRROR_PREFIXES):
        return ZONE_ADAPTER_MIRROR
    if _matches(rel_posix, READ_ONLY_EVIDENCE_PREFIXES):
        return ZONE_READ_ONLY_EVIDENCE
    if _matches(rel_posix, TOOL_OWNED_ROOT_PREFIXES):
        return ZONE_TOOL_OWNED_FORBIDDEN
    return ZONE_AMBIGUOUS_ESCALATE


def is_approved_write_seam(target: Path, path: Path) -> bool:
    """True only for the two zones a Toolchain Driver may write directly."""
    return classify_path(target, path) in (ZONE_HLDSPEC_OWNED, ZONE_ADAPTER_MIRROR)


def is_forbidden_write(target: Path, path: Path) -> bool:
    """True for every zone a Toolchain Driver must never write — including the
    default-deny ambiguous zone."""
    return not is_approved_write_seam(target, path)
