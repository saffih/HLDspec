from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from hldspec import journey3_driver as j3drv

_CLI_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hldspec_agent_session.py"


def _load_cli():
    spec = importlib.util.spec_from_file_location("hldspec_agent_session_cli", _CLI_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(target: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(target), *argv], text=True, capture_output=True, check=True)


def _snapshot_target(target: Path) -> dict[str, bytes]:
    """Byte snapshot of the entire target (excluding .git internals). The Journey 3
    driver is read-only, so this must be identical before and after a status run."""
    snapshot: dict[str, bytes] = {}
    for path in sorted(target.rglob("*")):
        if path.is_dir() or ".git" in path.parts:
            continue
        snapshot[path.relative_to(target).as_posix()] = path.read_bytes()
    return snapshot


class Journey3StatusCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = _load_cli()
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-journey3-status-cli-")
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

    def test_subcommand_is_registered(self) -> None:
        # journey3-status is wired into the normal dispatcher, not just a standalone script.
        parser = self.module.build_parser()
        args = parser.parse_args(["journey3-status", "--target", str(self.target)])
        self.assertIs(args.func, self.module.command_journey3_status)

    def test_text_output_renders_driver_status(self) -> None:
        exit_code, output = self._run(["journey3-status", "--target", str(self.target)])
        self.assertIn("# Journey 3 Driver", output)
        self.assertIn("NEXT SAFE ACTION", output)
        # An empty git target has no source package -> BLOCKED (exit 2).
        self.assertEqual(2, exit_code)
        self.assertIn(j3drv.STATUS_BLOCKED, output)

    def test_json_output_is_machine_readable(self) -> None:
        exit_code, output = self._run(["journey3-status", "--target", str(self.target), "--json"])
        report = json.loads(output)
        self.assertEqual(j3drv.SCHEMA_VERSION, report["schema_version"])
        self.assertIn("driver_status", report)
        self.assertEqual(report["driver_status"], j3drv.STATUS_BLOCKED)
        self.assertEqual(2, exit_code)
        # The driver self-attests it neither mutated nor executed.
        self.assertFalse(report["mutated_target"])
        self.assertFalse(report["executed_anything"])

    def test_no_phase_reports_unknown_phase(self) -> None:
        _exit_code, output = self._run(
            ["journey3-status", "--target", str(self.target), "--json", "--no-phase"]
        )
        report = json.loads(output)
        self.assertEqual(report["phase_source"], "not_provided")
        self.assertEqual(report["journey3_phase"], j3drv.PHASE_UNKNOWN_REQUIRES_READINESS_RUN)

    def test_default_target_is_cwd(self) -> None:
        # --target defaults to "." (preserves the standalone script default).
        parser = self.module.build_parser()
        args = parser.parse_args(["journey3-status"])
        self.assertEqual(args.target, ".")

    def test_status_never_mutates_target(self) -> None:
        # Seed representative tool-owned files; a read-only driver must touch nothing.
        for rel, content in {
            ".specify/memory/constitution.md": b"# Constitution\n\noriginal\n",
            "specs/001-foo/spec.md": b"# Spec\n\noriginal\n",
        }.items():
            path = self.target / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

        before = _snapshot_target(self.target)
        git_status_before = _git(self.target, "status", "--porcelain").stdout

        self._run(["journey3-status", "--target", str(self.target)])
        self._run(["journey3-status", "--target", str(self.target), "--json"])
        self._run(["journey3-status", "--target", str(self.target), "--no-phase"])

        self.assertEqual(before, _snapshot_target(self.target))
        self.assertEqual(git_status_before, _git(self.target, "status", "--porcelain").stdout)


if __name__ == "__main__":
    unittest.main()
