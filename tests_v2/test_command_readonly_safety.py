"""Brownfield first-touch read-only safety.

Characterizes which command-surface verbs mutate a fresh target's `.hldspec/`
control state on first touch. `status`, `doctor`, and `operator-state` carry
inspection-style names but DO write discovery/lifecycle/branch-gate reports into
the target when no controller pointer exists yet (the brownfield first-touch
case). Only `journey3-status` is genuinely read-only. These tests lock that
asymmetry so the honesty of the help text and docs cannot silently drift, and so
any future move to make the trap commands read-only is a deliberate, test-visible
change.

See README "First-touch / brownfield safety" and
docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md command-surface "First-touch / brownfield
rule".
"""
from __future__ import annotations

import importlib.util
import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

_CLI_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hldspec_agent_session.py"


def _load_cli():
    spec = importlib.util.spec_from_file_location("hldspec_agent_session_cli_safety", _CLI_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(target: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(target), *argv], text=True, capture_output=True, check=True)


class CommandReadonlySafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = _load_cli()
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-readonly-safety-")
        self.target = Path(self._tmp.name)
        # Fresh git target with no controller pointer (.hldspec-run.json) — the
        # brownfield first-touch case where writes resolve target-local.
        _git(self.target, "init", "-q")
        _git(self.target, "config", "user.email", "test@example.com")
        _git(self.target, "config", "user.name", "Test")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run(self, argv: list[str]) -> None:
        parser = self.module.build_parser()
        args = parser.parse_args(argv)
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)  # exit code irrelevant; we assert the write side effect

    def _assert_no_pointer(self) -> None:
        self.assertFalse(
            (self.target / ".hldspec-run.json").exists(),
            "precondition: target must have no controller pointer",
        )

    def test_status_writes_target_control_state(self) -> None:
        self._assert_no_pointer()
        self.assertFalse((self.target / ".hldspec").exists())
        self._run(["status", "--target", str(self.target)])
        # Trap: an inspection-named command created target-local control state.
        self.assertTrue((self.target / ".hldspec" / "sync").is_dir())

    def test_doctor_writes_target_control_state(self) -> None:
        self._assert_no_pointer()
        self.assertFalse((self.target / ".hldspec").exists())
        self._run(["doctor", "--target", str(self.target)])
        self.assertTrue((self.target / ".hldspec" / "sync").is_dir())

    def test_operator_state_writes_target_control_state(self) -> None:
        self._assert_no_pointer()
        self.assertFalse((self.target / ".hldspec").exists())
        self._run(["operator-state", "--target", str(self.target)])
        self.assertTrue((self.target / ".hldspec" / "sync").is_dir())

    def test_journey3_status_is_read_only(self) -> None:
        # The safe brownfield first-touch entrypoint: never creates .hldspec/.
        self._assert_no_pointer()
        self.assertFalse((self.target / ".hldspec").exists())
        self._run(["journey3-status", "--target", str(self.target)])
        self.assertFalse(
            (self.target / ".hldspec").exists(),
            "journey3-status must remain read-only on a brownfield first touch",
        )


if __name__ == "__main__":
    unittest.main()
