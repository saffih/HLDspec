#!/usr/bin/env python3
"""Proof Target Init -- builds the tiny brownfield repo the E2E proof harness drives.

Creates an isolated `calc` package with a passing test at `/tmp/proof-target` and an
HLD at `/tmp/proof-target-HLD.md` describing one small brownfield change (add a
`subtract` function alongside the existing `add`). This is a *fixture builder*, not a
product feature: it never touches a real product repo. Its destructive reset is
guarded to only ever remove paths under a system temp root.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_TARGET = Path("/tmp/proof-target")
DEFAULT_HLD = Path("/tmp/proof-target-HLD.md")

CALC_INIT = """from calc.core import add

__all__ = ["add"]
"""

CALC_CORE = """def add(a, b):
    return a + b
"""

TEST_CORE = """from calc import add


def test_add():
    assert add(2, 3) == 5
"""

README = """# proof-target

Isolated brownfield fixture for the HLDspec E2E proof harness. This is not a real
project; it is recreated from scratch by `scripts/proof_target_init.py`.
"""

# The proof harness writes its report under `.hldspec-proof/`. Ignoring + committing
# this in the seed keeps the target clean across repeated runs, so a second smoke run
# is never falsely BLOCKED merely because a prior report exists.
GITIGNORE = """.hldspec-proof/
"""

HLD = """# proof-target HLD

## Current capability
- `add(a, b)` lives in `calc/core.py` and is exposed from `calc/__init__.py`.
- `tests/test_core.py` has `test_add`.

## New capability
- `subtract(a, b)` returning `a - b`.

## Acceptance criteria
- add `subtract(a, b)` to `calc/core.py`
- expose `subtract` from `calc/__init__.py`
- add `test_subtract` to `tests/test_core.py`
- do not change `add`
- do not remove `test_add`
- no CLI
- no I/O
- no external dependencies
"""


def _temp_roots() -> tuple[Path, ...]:
    """System temp roots a destructive reset is allowed to touch."""
    roots = [Path("/tmp"), Path(tempfile.gettempdir())]
    seen: list[Path] = []
    for root in roots:
        rp = Path(os.path.realpath(root))
        if rp not in seen:
            seen.append(rp)
    return tuple(seen)


def _is_under_temp(path: Path) -> bool:
    """True only if `path` is *strictly under* a temp root (never the root itself)."""
    ap = Path(os.path.realpath(os.path.abspath(path)))
    for root in _temp_roots():
        try:
            rel = ap.relative_to(root)
        except ValueError:
            continue
        if rel.parts:  # at least one component below the root
            return True
    return False


def _reset_path(path: Path) -> None:
    """Remove `path` (file or dir). Refuses anything not strictly under a temp root."""
    if not _is_under_temp(path):
        raise ValueError(
            f"refusing destructive reset of path outside a temp root: {path}"
        )
    if path.is_symlink():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _git(target: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(target), *args],
        text=True,
        capture_output=True,
        check=True,
        timeout=60,
    )


def init_proof_target(
    target: Path | str = DEFAULT_TARGET,
    hld_path: Path | str = DEFAULT_HLD,
) -> dict[str, Any]:
    """Create the isolated brownfield fixture + HLD. Returns a summary dict.

    Destructive only against `target` and `hld_path`, both of which must be under a
    temp root (guarded by `_reset_path`).
    """
    target = Path(target)
    hld_path = Path(hld_path)

    _reset_path(target)
    _reset_path(hld_path)

    (target / "calc").mkdir(parents=True)
    (target / "calc" / "__init__.py").write_text(CALC_INIT)
    (target / "calc" / "core.py").write_text(CALC_CORE)
    (target / "tests").mkdir()
    (target / "tests" / "test_core.py").write_text(TEST_CORE)
    (target / "README.md").write_text(README)
    (target / ".gitignore").write_text(GITIGNORE)

    _git(target, "init", "-q")
    _git(target, "add", "-A")
    _git(
        target,
        "-c",
        "user.email=proof@example.invalid",
        "-c",
        "user.name=proof-harness",
        "commit",
        "-q",
        "-m",
        "initial proof target: add(a, b)",
    )

    pytest_proc = subprocess.run(
        ["python3", "-m", "pytest", "tests/", "-q"],
        cwd=str(target),
        text=True,
        capture_output=True,
        timeout=120,
    )

    hld_path.write_text(HLD)

    return {
        "target": str(target),
        "hld": str(hld_path),
        "pytest_returncode": pytest_proc.returncode,
        "pytest_stdout": pytest_proc.stdout,
        "pytest_stderr": pytest_proc.stderr,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the E2E proof target fixture.")
    parser.add_argument("--target", default=str(DEFAULT_TARGET))
    parser.add_argument("--hld", default=str(DEFAULT_HLD))
    args = parser.parse_args(argv)

    result = init_proof_target(Path(args.target), Path(args.hld))
    print(f"target: {result['target']}")
    print(f"hld: {result['hld']}")
    if result["pytest_returncode"] == 0:
        print("initial pytest: PASS")
        return 0
    print(f"initial pytest: FAIL (returncode={result['pytest_returncode']})")
    print(result["pytest_stdout"])
    print(result["pytest_stderr"])
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
