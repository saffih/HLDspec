from __future__ import annotations

import importlib.util
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


probe = _load("proof_speckit_skill_evidence", "proof_speckit_skill_evidence.py")


def _make_target(tmp: str, *, specify: bool, skills: bool) -> Path:
    target = Path(tmp) / "proof-target"
    target.mkdir()
    if specify:
        (target / ".specify").mkdir()
    if skills:
        skill_dir = target / ".claude" / "skills" / "speckit-specify"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# speckit-specify\n")
    return target


class SkillEvidenceTests(unittest.TestCase):
    def test_present_requires_both_signals(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            target = _make_target(d, specify=True, skills=True)
            report = probe.probe_skill_evidence(target)
            self.assertEqual(report["verdict"], "SKILL_EVIDENCE_PRESENT")
            self.assertTrue(report["specify_dir_present"])
            self.assertTrue(report["speckit_skills_present"])
            self.assertIn(".claude/skills/speckit-specify/SKILL.md", report["speckit_skill_files"])

    def test_specify_only_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            target = _make_target(d, specify=True, skills=False)
            report = probe.probe_skill_evidence(target)
            self.assertEqual(report["verdict"], "SKILL_EVIDENCE_MISSING")
            self.assertTrue(report["specify_dir_present"])
            self.assertFalse(report["speckit_skills_present"])
            self.assertEqual(report["speckit_skill_files"], [])

    def test_skills_only_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            target = _make_target(d, specify=False, skills=True)
            report = probe.probe_skill_evidence(target)
            self.assertEqual(report["verdict"], "SKILL_EVIDENCE_MISSING")
            self.assertFalse(report["specify_dir_present"])
            self.assertTrue(report["speckit_skills_present"])

    def test_neither_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            target = _make_target(d, specify=False, skills=False)
            report = probe.probe_skill_evidence(target)
            self.assertEqual(report["verdict"], "SKILL_EVIDENCE_MISSING")

    def test_nonexistent_target_is_missing_not_error(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            report = probe.probe_skill_evidence(Path(d) / "does-not-exist")
            self.assertEqual(report["verdict"], "SKILL_EVIDENCE_MISSING")
            self.assertFalse(report["specify_dir_present"])
            self.assertFalse(report["speckit_skills_present"])

    def test_evidence_is_not_execution_proof_contract(self) -> None:
        # The "evidence != proof" claim must be a falsifiable, present field, and the
        # probe must declare it neither mutated nor ran anything.
        with tempfile.TemporaryDirectory() as d:
            target = _make_target(d, specify=True, skills=True)
            report = probe.probe_skill_evidence(target)
            self.assertIn("not execution proof", report["disclaimer"])
            self.assertIn("HLDSPEC_LIVE_E2E", report["live_proof_gate"])
            self.assertFalse(report["mutated_target"])
            self.assertFalse(report["ran_subprocess"])

    def test_probe_writes_nothing_into_target(self) -> None:
        # Non-stateful: the on-disk layout is identical before and after probing.
        with tempfile.TemporaryDirectory() as d:
            target = _make_target(d, specify=True, skills=True)
            before = sorted(p.relative_to(target).as_posix() for p in target.rglob("*"))
            probe.probe_skill_evidence(target)
            after = sorted(p.relative_to(target).as_posix() for p in target.rglob("*"))
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
