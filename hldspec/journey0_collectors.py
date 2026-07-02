"""Read-only Journey 0 evidence collectors.

Slice B only: collect shallow observed file evidence from explicit paths and
return typed Journey 0 artifact models. This module does not classify evidence,
produce gate results, create handoffs, mutate targets, or add an automation
surface.
"""
from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from hldspec.journey0_artifacts import (
    BrownfieldEvidencePack,
    EvidenceItem,
    EvidenceLabel,
)

DEFAULT_INCLUDE_FILE_GLOBS: tuple[str, ...] = (
    "*.md",
    "*.txt",
    "*.rst",
    "*.py",
    "*.js",
    "*.jsx",
    "*.ts",
    "*.tsx",
    "*.json",
    "*.yaml",
    "*.yml",
    "*.toml",
)

IGNORED_DIR_NAMES: frozenset[str] = frozenset(
    {
        "." + "g" + "it",
        ".cache",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "coverage",
        "dist",
        "node_modules",
        "venv",
    }
)

def collect_journey0_observed_evidence(
    root: str | Path,
    *,
    include_file_globs: tuple[str, ...] | None = None,
) -> BrownfieldEvidencePack:
    """Collect observed file evidence from an explicit root/path.

    The collector is intentionally shallow: each included file becomes one
    OBSERVED evidence row. It records file presence, rough source type, and
    relative path. It does not read file content, infer product behavior, or
    resolve conflicts.
    """

    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(root_path)

    globs = include_file_globs or DEFAULT_INCLUDE_FILE_GLOBS
    files = _iter_included_files(root_path, globs)
    evidence = tuple(
        _evidence_for_file(idx, path, root_path)
        for idx, path in enumerate(files, start=1)
    )
    return BrownfieldEvidencePack(evidence=evidence)


def _iter_included_files(root: Path, globs: tuple[str, ...]) -> tuple[Path, ...]:
    if root.is_file():
        return (root,) if _matches(root.name, globs) else ()

    included: list[Path] = []
    for current, dirnames, filenames in os.walk(root, topdown=True):
        dirnames[:] = sorted(
            dirname for dirname in dirnames if dirname not in IGNORED_DIR_NAMES
        )
        current_path = Path(current)
        for filename in sorted(filenames):
            path = current_path / filename
            if path.is_symlink():
                continue
            rel = path.relative_to(root).as_posix()
            if _matches(rel, globs) or _matches(filename, globs):
                included.append(path)
    return tuple(sorted(included, key=lambda path: path.relative_to(root).as_posix()))


def _matches(name: str, globs: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in globs)


def _evidence_for_file(
    index: int,
    path: Path,
    root: Path,
) -> EvidenceItem:
    rel = _source_ref(path, root)
    source_type = _source_type(path, rel)
    summary = f"{source_type} file observed: {rel}"
    return EvidenceItem(
        evidence_id=f"EVIDENCE-{index:03d}",
        source_type=source_type,
        source_ref=rel,
        source_location=rel,
        summary=summary,
        label=EvidenceLabel.OBSERVED,
        confidence="high",
    )


def _source_ref(path: Path, root: Path) -> str:
    if root.is_file():
        return path.name
    return path.relative_to(root).as_posix()


def _source_type(path: Path, rel: str) -> str:
    parts = set(Path(rel).parts)
    suffix = path.suffix.lower()
    name = path.name.lower()
    if ".specify" in parts or "specs" in parts:
        return "old_spec_state"
    if ".hldspec" in parts:
        return "prior_hldspec_state"
    if "test" in name or "tests" in parts:
        return "test_file"
    if name.startswith("hld") or "hld" in name:
        return "hld_fragment"
    if suffix in {".py", ".js", ".jsx", ".ts", ".tsx"}:
        return "code_file"
    if suffix in {".md", ".txt", ".rst"}:
        return "doc_file"
    return "resource_file"
