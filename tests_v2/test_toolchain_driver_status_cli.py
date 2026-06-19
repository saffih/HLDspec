from __future__ import annotations

import importlib.util
import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from hldspec import helper_selection as hsel
from hldspec import refresh_target as rt
from hldspec import run_state
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

    def test_status_includes_driver_section_with_runtime_identity(self) -> None:
        rt.refresh_target(self.target, apply=True)
        hsel.write_helper_selection(self.target, "speckit", selected_by="human")

        _exit_code, output = self._run(["status", "--target", str(self.target)])

        self.assertIn("## Driver", output)
        self.assertIn("Actor: human", output)
        self.assertIn("Authority: GUIDE_ONLY", output)
        self.assertIn("Status: PASS", output)
        self.assertIn("Effective helper: speckit", output)
        self.assertIn("Installed runtime helper: speckit", output)
        self.assertIn("Installed runtime toolchain: SpecKit", output)
        self.assertIn("Identity match: true", output)

    def test_status_driver_section_shows_authority_contract(self) -> None:
        rt.refresh_target(self.target, apply=True)
        hsel.write_helper_selection(self.target, "speckit", selected_by="human")

        _exit_code, output = self._run(["status", "--target", str(self.target)])

        self.assertIn("Actor: human", output)
        self.assertIn("Authority: GUIDE_ONLY", output)
        self.assertIn("Observation: allowed", output)
        # Execution and mutation are surfaced separately, never conflated.
        self.assertIn("Execution: not allowed", output)
        self.assertIn("Mutation: not allowed", output)
        # Operator vs approver distinction is explicit and never conflated.
        self.assertIn("Operator replacement:", output)
        self.assertIn("Approver replacement: not allowed", output)
        self.assertIn("Protected approvals (owner-only):", output)

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


class ToolchainStatusCliExternalStateTests(unittest.TestCase):
    """External-state mode: the target carries only the `.hldspec-run.json`
    pointer; real control state lives under the controller root. Covers the
    residual risk that CLI-level status/select-helper might mutate
    target-owned/tool-owned files or leak helper selection into the target."""

    def setUp(self) -> None:
        self.module = _load_cli()
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-toolchain-status-cli-external-")
        root = Path(self._tmp.name)
        self.target = root / "target"
        self.controller = root / "controller"
        self.target.mkdir()
        (self.controller / ".hldspec").mkdir(parents=True)
        _git(self.target, "init", "-q")
        _git(self.target, "config", "user.email", "test@example.com")
        _git(self.target, "config", "user.name", "Test")
        source = self.target / "HLD.md"
        source.write_text("# HLD\n", encoding="utf-8")
        run_state.write_pointer(
            self.target,
            controller_root=self.controller,
            source=source,
            source_hash="deadbeef",
            mode="update",
            agent="test",
            workflow_trigger="build_loop_ready",
            created_or_updated_at="2026-06-07T00:00:00+00:00",
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run(self, argv: list[str]) -> tuple[int, str]:
        parser = self.module.build_parser()
        args = parser.parse_args(argv)
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = args.func(args)
        return exit_code, buf.getvalue()

    def test_status_and_select_helper_external_mode_safety(self) -> None:
        before = _seed_toolchain_owned_files(self.target)
        snapshot_before = _snapshot_forbidden_zone(self.target)
        self.assertGreaterEqual(len(snapshot_before), len(before))
        git_status_before = _git(self.target, "status", "--porcelain").stdout

        self._run(["status", "--target", str(self.target)])
        exit_code, output = self._run(
            ["select-helper", "--target", str(self.target), "--use-recommended"]
        )
        self._run(["status", "--target", str(self.target)])

        self.assertEqual(0, exit_code)
        self.assertIn("Selected helper: speckit", output)

        # Seeded .specify/ and specs/ bytes are untouched.
        snapshot_after = _snapshot_forbidden_zone(self.target)
        self.assertEqual(snapshot_before, snapshot_after)

        # Helper selection lands only under the controller root, never the target.
        self.assertTrue((self.controller / ".hldspec" / "helper_selection.json").is_file())
        self.assertFalse((self.target / ".hldspec" / "helper_selection.json").exists())

        # No git mutation in the product target repo (status stays GUIDE_ONLY-safe).
        git_status_after = _git(self.target, "status", "--porcelain").stdout
        self.assertEqual(git_status_before, git_status_after)


if __name__ == "__main__":
    unittest.main()
