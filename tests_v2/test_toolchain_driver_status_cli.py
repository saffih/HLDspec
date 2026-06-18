from __future__ import annotations

import importlib.util
import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from hldspec import helper_selection as hsel
from hldspec import toolchain_driver_boundary as tdb

_CLI_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hldspec_agent_session.py"


def _load_cli():
    spec = importlib.util.spec_from_file_location("hldspec_agent_session_cli", _CLI_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(target: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(target), *argv], text=True, capture_output=True, check=True)


def _seed_toolchain_owned_files(target: Path) -> dict[str, bytes]:
    """Create representative SpecKit-owned files in every forbidden zone and
    return their relative-path -> content snapshot."""
    files = {
        ".specify/memory/constitution.md": b"# Constitution\n\noriginal content\n",
        ".specify/templates/spec-template.md": b"# Spec Template\n",
        "specs/001-foo/spec.md": b"# Spec\n\noriginal spec\n",
        "specs/001-foo/plan.md": b"# Plan\n",
    }
    for rel, content in files.items():
        path = target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return files


def _snapshot_forbidden_zone(target: Path) -> dict[str, bytes]:
    snapshot: dict[str, bytes] = {}
    for path in target.rglob("*"):
        if path.is_dir() or ".git" in path.parts:
            continue
        if tdb.is_approved_write_seam(target, path):
            continue
        rel = path.relative_to(target).as_posix()
        snapshot[rel] = path.read_bytes()
    return snapshot


class ToolchainStatusCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = _load_cli()
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-toolchain-status-cli-")
        self.target = Path(self._tmp.name)
        _git(self.target, "init", "-q")
        _git(self.target, "config", "user.email", "test@example.com")
        _git(self.target, "config", "user.name", "Test")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run(self, argv: list[str]) -> tuple[int, str]:
        parser = self.module.build_parser()
        args = parser.parse_args(argv)
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = args.func(args)
        return exit_code, buf.getvalue()

    def test_status_includes_toolchain_section_with_no_selection(self) -> None:
        _exit_code, output = self._run(["status", "--target", str(self.target)])
        self.assertIn("## Toolchain", output)
        self.assertIn("Toolchain: SpecKit", output)
        self.assertIn("Recommended helper: speckit", output)
        self.assertIn("Selected helper: none", output)

    def test_select_helper_writes_selection_and_status_reflects_it(self) -> None:
        exit_code, output = self._run(["select-helper", "--target", str(self.target), "--use-recommended"])
        self.assertEqual(0, exit_code)
        self.assertIn("Selected helper: speckit", output)
        self.assertIsNotNone(hsel.read_helper_selection(self.target))

        _exit_code, status_output = self._run(["status", "--target", str(self.target)])
        self.assertIn("Selected helper: speckit", status_output)
        self.assertIn("Effective helper: speckit", status_output)

    def test_select_helper_rejects_planned_helper(self) -> None:
        exit_code, _output = self._run(
            ["select-helper", "--target", str(self.target), "--helper-id", "codex"]
        )
        self.assertEqual(2, exit_code)
        self.assertIsNone(hsel.read_helper_selection(self.target))

    def test_status_and_select_helper_never_mutate_tool_owned_zones(self) -> None:
        before = _seed_toolchain_owned_files(self.target)
        snapshot_before = _snapshot_forbidden_zone(self.target)
        self.assertGreaterEqual(len(snapshot_before), len(before))

        self._run(["status", "--target", str(self.target)])
        self._run(["select-helper", "--target", str(self.target), "--use-recommended"])
        self._run(["status", "--target", str(self.target)])

        snapshot_after = _snapshot_forbidden_zone(self.target)
        self.assertEqual(snapshot_before, snapshot_after)


if __name__ == "__main__":
    unittest.main()
