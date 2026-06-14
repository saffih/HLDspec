"""Vendor a minimal, self-contained, read-only Journey 3 run-card runtime.

`hldspec refresh-target --apply` copies the live source of the modules that the
read-only next-feature readiness driver needs into the target's
``.hldspec/runtime/hldspec/`` package, plus a small entry script, ``VERSION``,
and ``MANIFEST.json``. After that the target's ``.hldspec/bin/run-card`` runs
entirely from the vendored copy -- it never imports from the HLDspec checkout
and never needs ``HLDSPEC_HOME``.

The vendored module set is computed by walking the intra-package import closure
of ``next_feature_readiness`` (the seed), so it stays minimal and never drifts:
whatever the live driver imports today is exactly what gets vendored. All those
modules are stdlib + intra-package only (no third-party deps, no network).

This module is part of the HLDspec checkout (the installer side). It is not
itself vendored; only the closure it computes is.
"""
from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path
from typing import Callable

from .refresh_target import RUNTIME_RELDIR  # single source of truth for the layout root

# Bump when the vendoring format (layout/entry/manifest) changes.
RUNTIME_VERSION = "1"

# Seed of the import closure: the read-only run-card driver.
RUNTIME_SEED = ("next_feature_readiness",)

_PKG_DIR = Path(__file__).resolve().parent  # the live hldspec/ package
_PKG_NAME = "hldspec"

# Target-relative locations of the vendored runtime.
RUNTIME_PKG_RELDIR = RUNTIME_RELDIR / _PKG_NAME
RUNTIME_ENTRY_RELPATH = RUNTIME_RELDIR / "run_card_main.py"
RUNTIME_VERSION_RELPATH = RUNTIME_RELDIR / "VERSION"
RUNTIME_MANIFEST_RELPATH = RUNTIME_RELDIR / "MANIFEST.json"


def _module_level_imports(body: list[ast.stmt]) -> list[ast.stmt]:
    """Import statements reachable at module load time.

    Descends into control-flow (if/try/with) but never into function or class
    bodies, so lazy/function-local imports of installer-only helpers (e.g.
    refresh_target importing runtime_vendor inside its apply handler) are
    excluded -- keeping the vendored runtime minimal.
    """
    imports: list[ast.stmt] = []
    for node in body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(node)
        elif isinstance(node, (ast.If, ast.Try, ast.With)):
            for attr in ("body", "orelse", "finalbody", "handlers"):
                block = getattr(node, attr, None) or []
                for item in block:
                    if isinstance(item, ast.ExceptHandler):
                        imports.extend(_module_level_imports(item.body))
                    else:
                        imports.extend(_module_level_imports([item]))
    return imports


def _local_imported_modules(path: Path) -> set[str]:
    """Top-level intra-package module names imported by `path` (load time only)."""
    mods: set[str] = set()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in _module_level_imports(tree.body):
        if isinstance(node, ast.ImportFrom):
            if node.level == 1:  # `from . import X` or `from .X import Y`
                if node.module:
                    mods.add(node.module.split(".")[0])
                else:
                    for alias in node.names:
                        mods.add(alias.name.split(".")[0])
            elif node.module and node.module.split(".")[0] == _PKG_NAME:
                parts = node.module.split(".")
                if len(parts) > 1:
                    mods.add(parts[1])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == _PKG_NAME and "." in alias.name:
                    mods.add(alias.name.split(".")[1])
    return mods


def collect_runtime_modules() -> dict[str, Path]:
    """Return {module_name: source_path} for the full closure from the seed.

    Raises if a referenced module is not a flat ``hldspec/<name>.py`` file --
    the current closure is entirely flat, and a sub-package would need explicit
    handling rather than silent omission.
    """
    resolved: dict[str, Path] = {}
    stack = list(RUNTIME_SEED)
    while stack:
        name = stack.pop()
        if name in resolved:
            continue
        path = _PKG_DIR / f"{name}.py"
        if not path.is_file():
            raise FileNotFoundError(
                f"runtime closure references '{_PKG_NAME}.{name}', which is not a flat "
                f"module file ({path}); update runtime_vendor to handle it."
            )
        resolved[name] = path
        stack.extend(_local_imported_modules(path))
    return resolved


def _source_commit(run: Callable[..., subprocess.CompletedProcess[str]] | None = None) -> str:
    runner = run or subprocess.run
    try:
        completed = runner(
            ["git", "-C", str(_PKG_DIR), "rev-parse", "--short", "HEAD"],
            cwd=str(_PKG_DIR),
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return "unknown"
    if completed.returncode != 0:
        return "unknown"
    return completed.stdout.strip() or "unknown"


def runtime_entry_source() -> str:
    """The vendored read-only entry script (`.hldspec/runtime/run_card_main.py`).

    Pure read: builds and prints the run card from the vendored driver; it does
    not persist report files, run SpecKit, or mutate git.
    """
    return '''#!/usr/bin/env python3
"""Vendored, self-contained, READ-ONLY Journey 3 run-card entry.

Runs entirely from this `.hldspec/runtime/` directory. It never imports from
an HLDspec checkout and never needs HLDSPEC_HOME. It only reads this repo's
files and runs read-only git commands, then prints the SpecKit run card.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_RUNTIME_DIR = Path(__file__).resolve().parent
if str(_RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(_RUNTIME_DIR))

from hldspec import next_feature_readiness as nfr  # vendored copy


def _runtime_footer() -> str:
    manifest = _RUNTIME_DIR / "MANIFEST.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    return (
        f"\\n_Vendored run-card runtime v{data.get('runtime_version')} "
        f"(source {data.get('source_commit')}), generated by {data.get('generated_by')}._\\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Journey 3 SpecKit run card (vendored).")
    parser.add_argument("--target", default=os.getcwd(), help="Target repo (default: current directory).")
    args = parser.parse_args(argv)

    target = Path(args.target).expanduser().resolve()
    report = nfr.build_next_feature_readiness_report(target)
    sys.stdout.write(nfr.render_next_feature_readiness_report(report))
    sys.stdout.write(_runtime_footer())
    return 0 if report.get("safety_status") == nfr.SAFETY_PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
'''


def build_manifest(
    modules: dict[str, Path],
    *,
    run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> dict:
    files = [str(RUNTIME_PKG_RELDIR / "__init__.py")]
    files.extend(str(RUNTIME_PKG_RELDIR / f"{name}.py") for name in sorted(modules))
    files.append(str(RUNTIME_ENTRY_RELPATH))
    return {
        "runtime_version": RUNTIME_VERSION,
        "generated_by": "hldspec refresh-target",
        "source_commit": _source_commit(run=run),
        "files": files,
    }


def runtime_files(
    *,
    run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, str]:
    """Return {target_relative_path: file_contents} for the whole vendored runtime."""
    modules = collect_runtime_modules()
    out: dict[str, str] = {}
    out[str(RUNTIME_PKG_RELDIR / "__init__.py")] = '"""Vendored HLDspec runtime (read-only).\n"""\n'
    for name, src in modules.items():
        out[str(RUNTIME_PKG_RELDIR / f"{name}.py")] = src.read_text(encoding="utf-8")
    out[str(RUNTIME_ENTRY_RELPATH)] = runtime_entry_source()
    out[str(RUNTIME_VERSION_RELPATH)] = RUNTIME_VERSION + "\n"
    manifest = build_manifest(modules, run=run)
    out[str(RUNTIME_MANIFEST_RELPATH)] = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    return out
