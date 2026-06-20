from __future__ import annotations

import importlib.util
import json
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


doctor = _load("proof_speckit_readiness", "proof_speckit_readiness.py")


def _fake_runner(returncode=0, stdout="", stderr="", timed_out=False, not_found=False):
    def runner(cmd, *, cwd=None, timeout=None, env=None):
        return {
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": timed_out,
            "not_found": not_found,
        }

    return runner


def _which(claude=True, specify=False):
    def which(name):
        if name == "claude":
            return "/usr/bin/claude" if claude else None
        if name in ("specify", "spec-kit", "uvx"):
            return f"/usr/bin/{name}" if specify else None
        return None

    return which


class ReadinessClassificationTests(unittest.TestCase):
    def _classify(self, tmp, *, specify_dir=False, runner=None, which=None, smoke_command=None):
        target = Path(tmp) / "proof-target"
        target.mkdir()
        if specify_dir:
            (target / ".specify").mkdir()
        return doctor.classify_readiness(
            target, model="haiku", runner=runner or _fake_runner(),
            which=which or _which(claude=True), env={}, smoke_command=smoke_command,
        )

    def test_claude_missing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            report = self._classify(d, runner=_fake_runner(), which=_which(claude=False))
            self.assertEqual(report["status"], "CLAUDE_MISSING")

    def test_model_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            runner = _fake_runner(returncode=1, stdout="There's an issue with the selected model (haiku).")
            report = self._classify(d, runner=runner)
            self.assertEqual(report["status"], "MODEL_REJECTED")

    def test_unknown_command(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            # Wrong dot spelling -> unknown command -> the hyphen alternate is suggested.
            runner = _fake_runner(returncode=0, stdout="Unknown command: /speckit.specify")
            report = self._classify(d, runner=runner, smoke_command="/speckit.specify say only SMOKE_OK")
            self.assertEqual(report["status"], "UNKNOWN_COMMAND")
            self.assertTrue(any("/speckit-specify" in n for n in report["notes"]))

    def test_skill_unavailable_when_specify_present(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            runner = _fake_runner(returncode=0, stdout="The skill `speckit.specify` is not available.")
            report = self._classify(d, specify_dir=True, runner=runner)
            self.assertEqual(report["status"], "SKILL_UNAVAILABLE")

    def test_target_not_speckit_ready_when_no_specify(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            runner = _fake_runner(returncode=0, stdout="The skill `speckit.specify` is not available.")
            report = self._classify(d, specify_dir=False, runner=runner)
            self.assertEqual(report["status"], "TARGET_NOT_SPECKIT_READY")

    def test_smoke_pass(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            runner = _fake_runner(returncode=0, stdout="SMOKE_OK\n")
            report = self._classify(d, specify_dir=True, runner=runner)
            self.assertEqual(report["status"], "SMOKE_PASS")

    def test_hollow_completion_does_not_pass(self) -> None:
        # Marker must block before the standalone-token check (PO:SI guard).
        prose = "The skill `speckit.specify` is not available.\nSMOKE_OK\n"
        with tempfile.TemporaryDirectory() as d:
            runner = _fake_runner(returncode=0, stdout=prose)
            report = self._classify(d, specify_dir=False, runner=runner)
            self.assertEqual(report["status"], "TARGET_NOT_SPECKIT_READY")
            self.assertNotEqual(report["status"], "SMOKE_PASS")

    def test_unsafe_target_refused_before_probing(self) -> None:
        # A non-temp target is refused before claude/smoke even when the runner would PASS.
        report = doctor.classify_readiness(
            "/Users/nobody/real-repo", model="haiku",
            runner=_fake_runner(returncode=0, stdout="SMOKE_OK\n"),
            which=_which(claude=True), env={},
        )
        self.assertEqual(report["status"], "UNSAFE_TARGET")
        self.assertEqual(report["verdict"], "BLOCKED")

    def test_target_not_clean(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "proof-target"
            target.mkdir()
            report = doctor.classify_readiness(
                target, model="haiku", git_clean=lambda t: False,
                runner=_fake_runner(returncode=0, stdout="SMOKE_OK\n"),
                which=_which(claude=True), env={},
            )
            self.assertEqual(report["status"], "TARGET_NOT_CLEAN")
            self.assertEqual(report["verdict"], "BLOCKED")

    def test_clean_unknown_does_not_block(self) -> None:
        # Not a git repo -> cleanliness gate is N/A (None) and the ladder proceeds.
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "proof-target"
            target.mkdir()
            (target / ".specify").mkdir()
            report = doctor.classify_readiness(
                target, model="haiku", git_clean=lambda t: None,
                runner=_fake_runner(returncode=0, stdout="SMOKE_OK\n"),
                which=_which(claude=True), env={},
            )
            self.assertEqual(report["status"], "SMOKE_PASS")

    def test_hollow_completion_on_blank_success(self) -> None:
        # Exit 0, blank stdout, no marker, no token -> ran but produced nothing.
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "proof-target"
            target.mkdir()
            (target / ".specify").mkdir()
            report = doctor.classify_readiness(
                target, model="haiku",
                runner=_fake_runner(returncode=0, stdout="   \n"),
                which=_which(claude=True), env={},
            )
            self.assertEqual(report["status"], "HOLLOW_COMPLETION")
            self.assertEqual(report["verdict"], "BLOCKED")

    def test_report_written_with_exact_status(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "proof-target"
            target.mkdir()
            report = doctor.classify_readiness(
                target, model="haiku",
                runner=_fake_runner(returncode=0, stdout="The skill is not available."),
                which=_which(claude=True), env={},
            )
            json_path = target / doctor.REPORT_DIR_NAME / doctor.REPORT_JSON
            md_path = target / doctor.REPORT_DIR_NAME / doctor.REPORT_MD
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            data = json.loads(json_path.read_text())
            self.assertEqual(data["status"], report["status"])
            self.assertEqual(data["status"], "TARGET_NOT_SPECKIT_READY")


class PrepareRefusalTests(unittest.TestCase):
    def test_refuses_non_temp_target(self) -> None:
        with self.assertRaises(ValueError):
            doctor.propose_prepare("/Users/someone/real-repo", which=_which(specify=True))

    def test_proposes_only_never_executes_for_temp_target(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            proposal = doctor.propose_prepare(Path(d) / "proof-target", which=_which(specify=True))
            self.assertFalse(proposal["prepared"])  # never executes
            self.assertIn("PROPOSAL ONLY", proposal["note"])


class DefaultModeIsNonStatefulTests(unittest.TestCase):
    """The default CLI path must not invoke the stateful claude smoke.

    classify_readiness is the *only* path to the claude subprocess, so a tripwire
    on it proves the default path runs no stateful smoke. Paired with a --live test
    so the tripwire cannot pass vacuously on broken flag wiring.
    """

    def _tripwire(self):
        calls = []
        original = doctor.classify_readiness

        def spy(*args, **kwargs):
            calls.append((args, kwargs))
            return {
                "verdict": "BLOCKED",
                "status": doctor.STATUS_SKILL_UNAVAILABLE,
                "remediation": "stub",
                "target": kwargs.get("target") or (args[0] if args else ""),
            }

        return calls, original, spy

    def test_default_path_does_not_invoke_stateful_smoke(self) -> None:
        calls, original, spy = self._tripwire()
        doctor.classify_readiness = spy
        try:
            with tempfile.TemporaryDirectory() as d:
                target = Path(d) / "proof-target"
                (target / ".specify").mkdir(parents=True)
                skill = target / ".claude" / "skills" / "speckit-specify"
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text("# x\n")
                rc = doctor.main(["--target", str(target)])  # no --live
        finally:
            doctor.classify_readiness = original
        self.assertEqual(calls, [])  # stateful smoke never invoked
        self.assertEqual(rc, 0)  # both evidence signals present -> exit 0

    def test_default_path_missing_evidence_exits_nonzero(self) -> None:
        calls, original, spy = self._tripwire()
        doctor.classify_readiness = spy
        try:
            with tempfile.TemporaryDirectory() as d:
                target = Path(d) / "proof-target"
                target.mkdir()  # neither .specify/ nor skill files
                rc = doctor.main(["--target", str(target)])
        finally:
            doctor.classify_readiness = original
        self.assertEqual(calls, [])  # still no stateful smoke
        self.assertEqual(rc, 1)

    def test_live_flag_opts_into_stateful_smoke(self) -> None:
        calls, original, spy = self._tripwire()
        doctor.classify_readiness = spy
        try:
            with tempfile.TemporaryDirectory() as d:
                target = Path(d) / "proof-target"
                target.mkdir()
                doctor.main(["--live", "--target", str(target)])
        finally:
            doctor.classify_readiness = original
        self.assertEqual(len(calls), 1)  # --live DID invoke the stateful path


if __name__ == "__main__":
    unittest.main()
