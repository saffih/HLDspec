from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


init_mod = _load("proof_target_init", "proof_target_init.py")
e2e = _load("proof_e2e_v0", "proof_e2e_v0.py")


def _make_clean_repo(tmp: Path) -> tuple[Path, Path]:
    """Build a clean, committed proof target + HLD under a temp dir."""
    target = tmp / "proof-target"
    hld = tmp / "proof-target-HLD.md"
    init_mod.init_proof_target(target, hld)
    return target, hld


class ProofTargetInitTests(unittest.TestCase):
    def test_init_creates_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            target, _ = _make_clean_repo(tmp)
            for rel in ("calc/__init__.py", "calc/core.py", "tests/test_core.py", "README.md", ".gitignore"):
                self.assertTrue((target / rel).exists(), rel)
            self.assertIn("def add", (target / "calc" / "core.py").read_text())

    def test_gitignore_excludes_report_dir_and_is_committed(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            target, _ = _make_clean_repo(tmp)
            self.assertIn(".hldspec-proof/", (target / ".gitignore").read_text())
            tracked = subprocess.run(
                ["git", "-C", str(target), "ls-files", ".gitignore"],
                text=True, capture_output=True,
            ).stdout
            self.assertIn(".gitignore", tracked)  # committed in the seed, not left untracked

    def test_hld_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            _, hld = _make_clean_repo(tmp)
            self.assertTrue(hld.exists())
            self.assertIn("subtract", hld.read_text())

    def test_initial_pytest_passes(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            target = tmp / "proof-target"
            hld = tmp / "proof-target-HLD.md"
            result = init_mod.init_proof_target(target, hld)
            self.assertEqual(result["pytest_returncode"], 0, result["pytest_stdout"])

    def test_reset_refuses_non_temp_path(self) -> None:
        with self.assertRaises(ValueError):
            init_mod._reset_path(Path("/Users/someone/real-repo"))


def _fake_runner(returncode=0, stdout="", stderr="", timed_out=False, not_found=False):
    calls = []

    def runner(cmd, *, cwd=None, timeout=None, env=None):
        calls.append({"cmd": cmd, "cwd": cwd, "timeout": timeout})
        return {
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": timed_out,
            "not_found": not_found,
        }

    runner.calls = calls
    return runner


class ProofRunnerPreconditionTests(unittest.TestCase):
    def test_refuses_missing_target(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            missing = Path(d) / "nope"
            report = e2e.run_proof(missing, Path(d) / "h.md", "C2", mode="smoke", allow_non_temp=True, runner=_fake_runner())
            self.assertEqual(report["status"], "BLOCKED")
            self.assertIn("does not exist", report["blocker"])

    def test_refuses_non_git_target(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "plain"
            target.mkdir()
            hld = Path(d) / "h.md"
            hld.write_text("hld")
            report = e2e.run_proof(target, hld, "C2", mode="smoke", allow_non_temp=True, runner=_fake_runner())
            self.assertEqual(report["status"], "BLOCKED")
            self.assertIn("not a git repo", report["blocker"])

    def test_refuses_dirty_target(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            target, hld = _make_clean_repo(tmp)
            (target / "dirty.txt").write_text("uncommitted")
            runner = _fake_runner(returncode=0, stdout="SMOKE_OK")
            report = e2e.run_proof(target, hld, "C2", mode="smoke", allow_non_temp=True, runner=runner)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertIn("not clean", report["blocker"])
            self.assertEqual(runner.calls, [])  # agent never invoked on a dirty target

    def test_refuses_non_temp_target_without_override(self) -> None:
        # Without --allow-non-temp-target, anything but /tmp/proof-target is refused.
        report = e2e.run_proof("/some/real/path", "/x.md", "C2", mode="smoke", runner=_fake_runner())
        self.assertEqual(report["status"], "BLOCKED")
        self.assertIn("allow-non-temp-target", report["blocker"])


class ProofRunnerModeTests(unittest.TestCase):
    def test_live_blocked_without_env(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            target, hld = _make_clean_repo(tmp)
            runner = _fake_runner()
            report = e2e.run_proof(target, hld, "C2", mode="live", allow_non_temp=True, runner=runner, env={})
            self.assertEqual(report["status"], "BLOCKED")
            self.assertIn("HLDSPEC_LIVE_E2E", report["blocker"])
            self.assertEqual(runner.calls, [])  # no agent call without the env gate

    def test_blocked_smoke_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            target, hld = _make_clean_repo(tmp)
            # Fake claude: exits 0 but never prints SMOKE_OK -> BLOCKED.
            runner = _fake_runner(returncode=0, stdout="no token here")
            report = e2e.run_proof(target, hld, "C2", mode="smoke", allow_non_temp=True, runner=runner, env={})
            self.assertEqual(report["status"], "BLOCKED")
            json_path = target / e2e.REPORT_DIR_NAME / e2e.PROOF_JSON
            md_path = target / e2e.REPORT_DIR_NAME / e2e.PROOF_MD
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            import json

            data = json.loads(json_path.read_text())
            self.assertEqual(data["status"], "BLOCKED")
            self.assertEqual(data["blocker_code"], "SMOKE_NOT_CONFIRMED")
            self.assertEqual(len(runner.calls), 1)

    def test_default_smoke_command_is_hyphen_style_and_configurable(self) -> None:
        # Hyphen is what `specify init` actually installs (.claude/skills/speckit-*);
        # dot fuzzy-matches and triggers a real-workflow side effect (see module docs).
        self.assertTrue(e2e.DEFAULT_SMOKE_COMMAND.startswith("/speckit-specify"))
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            target, hld = _make_clean_repo(tmp)
            # Default: hyphen-style command appears in the recorded command.
            r1 = e2e.run_proof(target, hld, "C2", mode="smoke", allow_non_temp=True,
                               runner=_fake_runner(returncode=0, stdout="nope"), env={})
            self.assertEqual(r1["command"][-1], e2e.DEFAULT_SMOKE_COMMAND)
            # Configurable override is honored verbatim.
            r2 = e2e.run_proof(target, hld, "C2", mode="smoke", allow_non_temp=True,
                               runner=_fake_runner(returncode=0, stdout="nope"), env={},
                               smoke_command="/speckit-specify custom SMOKE")
            self.assertEqual(r2["command"][-1], "/speckit-specify custom SMOKE")

    def test_unknown_command_classified_separately_with_alternate(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            target, hld = _make_clean_repo(tmp)
            # Someone uses the wrong dot spelling -> unknown command -> suggest hyphen.
            runner = _fake_runner(returncode=0, stdout="Unknown command: /speckit.specify")
            report = e2e.run_proof(target, hld, "C2", mode="smoke", allow_non_temp=True, runner=runner, env={},
                                   smoke_command="/speckit.specify say only SMOKE_OK")
            self.assertEqual(report["status"], "BLOCKED")
            self.assertEqual(report["blocker_code"], "UNKNOWN_COMMAND")
            self.assertIn("syntax", report["blocker"])  # distinguishes syntax vs missing-skill
            self.assertTrue(any("/speckit-specify" in n for n in report["notes"]))  # alternate spelling suggested

    def test_skill_unavailable_prose_is_blocked_not_pass(self) -> None:
        # Exact hollow-completion observed live: skill not installed, yet the model
        # echoes "SMOKE_OK" inside prose. Must be BLOCKED/SKILL_UNAVAILABLE, not PASS.
        prose = (
            "The skill `speckit.specify` is not available. \n\n"
            "If you'd like to respond with \"SMOKE_OK\", I can do that. Otherwise, let "
            "me know which skill you intended to use from the available options.\n"
        )
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            target, hld = _make_clean_repo(tmp)
            runner = _fake_runner(returncode=0, stdout=prose)
            report = e2e.run_proof(target, hld, "C2", mode="smoke", allow_non_temp=True, runner=runner, env={})
            self.assertEqual(report["status"], "BLOCKED")
            self.assertEqual(report["blocker_code"], "SKILL_UNAVAILABLE")

    def test_standalone_smoke_ok_line_passes(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            target, hld = _make_clean_repo(tmp)
            runner = _fake_runner(returncode=0, stdout="SMOKE_OK\n")
            report = e2e.run_proof(target, hld, "C2", mode="smoke", allow_non_temp=True, runner=runner, env={})
            self.assertEqual(report["status"], "PASS", report["blocker"])

    def test_smoke_confirmed_rejects_prose_echo(self) -> None:
        self.assertTrue(e2e.smoke_confirmed("SMOKE_OK"))
        self.assertTrue(e2e.smoke_confirmed('  "SMOKE_OK"  '))
        self.assertFalse(e2e.smoke_confirmed('I can respond with "SMOKE_OK" if you like'))

    def test_repeated_blocked_smoke_is_safe(self) -> None:
        # The report dir is gitignored, so a second run must not be falsely BLOCKED as
        # "not clean" merely because a prior .hldspec-proof/ report exists.
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            target, hld = _make_clean_repo(tmp)
            runner = _fake_runner(returncode=0, stdout="nope")
            first = e2e.run_proof(target, hld, "C2", mode="smoke", allow_non_temp=True, runner=runner, env={})
            self.assertEqual(first["blocker_code"], "SMOKE_NOT_CONFIRMED")
            second = e2e.run_proof(target, hld, "C2", mode="smoke", allow_non_temp=True, runner=runner, env={})
            self.assertEqual(second["status"], "BLOCKED")
            self.assertEqual(second["blocker_code"], "SMOKE_NOT_CONFIRMED")  # not a cleanliness block
            self.assertNotIn("not clean", second["blocker"] or "")
            # Tree still clean to git (report dir ignored).
            porcelain = subprocess.run(
                ["git", "-C", str(target), "status", "--porcelain"], text=True, capture_output=True
            ).stdout
            self.assertEqual(porcelain.strip(), "")


class BoundedDiffTests(unittest.TestCase):
    def test_accepts_expected_files_plus_report_dir(self) -> None:
        changed = [
            "calc/core.py",
            "calc/__init__.py",
            "tests/test_core.py",
            ".hldspec-proof/proof_e2e_v0.json",
        ]
        result = e2e.check_bounded_diff(changed, e2e.EXPECTED_LIVE_FILES)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["unexpected"], [])

    def test_rejects_unexpected_files(self) -> None:
        changed = ["calc/core.py", "calc/cli.py"]
        result = e2e.check_bounded_diff(changed, e2e.EXPECTED_LIVE_FILES)
        self.assertFalse(result["ok"])
        self.assertIn("calc/cli.py", result["unexpected"])


if __name__ == "__main__":
    unittest.main()
