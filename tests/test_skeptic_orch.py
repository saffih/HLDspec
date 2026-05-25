"""SKEPTIC-ORCH-001 — Evidence-quality REWORK_REQUIRED blocks orchestration.

Tests verify:
1. Failing fixture: REWORK_REQUIRED => not-ready (blocked)
2. Passing fixture: PASS => ready
3. Blocking message names the exact artifact path
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.review_runskeptic_evidence_quality import (
    STATUS_PASS,
    STATUS_REWORK,
    build_review,
)


def _full_cycle() -> dict:
    """A cycle with all required evidence fields."""
    return {
        "decision": "FIX",
        "recommendation": "Keep.",
        "observed_evidence": ["tests/: file exists"],
        "evidence_level": "observed",
        "confidence": "HIGH",
        "unknowns": "none",
        "verification": "run tests",
        "residual_risk": "low",
    }


def _incomplete_cycle() -> dict:
    """A cycle missing evidence fields (old producer shape)."""
    return {
        "cycle_id": "FILE-001",
        "area": "repo baseline",
        "aspect": "source_of_truth",
        "spotlight": "AGENTS.md",
        "decision": "FIX",
        "severity": "PASS",
        "finding": "File present.",
        "evidence": ["exists: AGENTS.md"],
        "recommendation": "Keep.",
        "affected_artifacts": ["AGENTS.md"],
        # Missing: observed_evidence, evidence_level, confidence, unknowns,
        #          verification, residual_risk
    }


def _meta_review_payload(cycles: list[dict]) -> dict:
    return {"schema_version": 1, "summary": {}, "cycles": cycles}


class TestEvidenceQualityGating(unittest.TestCase):

    def test_pass_cycles_return_pass(self) -> None:
        payload = _meta_review_payload([_full_cycle()])
        review = build_review(payload, source_path="fixture")
        self.assertEqual(STATUS_PASS, review["status"])

    def test_incomplete_cycles_return_rework(self) -> None:
        payload = _meta_review_payload([_incomplete_cycle()])
        review = build_review(payload, source_path="fixture")
        self.assertEqual(STATUS_REWORK, review["status"])

    def test_rework_review_has_blockers(self) -> None:
        payload = _meta_review_payload([_incomplete_cycle()])
        review = build_review(payload, source_path="fixture")
        blockers = [f for f in review["findings"] if f["severity"] == "BLOCKER"]
        self.assertTrue(len(blockers) > 0, "Expected blockers for incomplete cycle")

    def test_blocker_message_names_missing_field(self) -> None:
        payload = _meta_review_payload([_incomplete_cycle()])
        review = build_review(payload, source_path="fixture")
        blocker_fields = {f["field"] for f in review["findings"] if f["severity"] == "BLOCKER"}
        # All these fields are missing from the old incomplete shape
        for expected in ("evidence_level", "confidence", "verification", "residual_risk"):
            self.assertIn(expected, blocker_fields, f"Expected BLOCKER for '{expected}'")

    def test_mixed_cycles_rework_wins(self) -> None:
        """One incomplete cycle contaminates the whole review."""
        payload = _meta_review_payload([_full_cycle(), _incomplete_cycle()])
        review = build_review(payload, source_path="fixture")
        self.assertEqual(STATUS_REWORK, review["status"])

    def test_rework_review_fail_on_rework_exit_code(self) -> None:
        """--fail-on-rework causes exit code 2."""
        import subprocess
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(__file__).parent.parent
            meta_json = Path(tmpdir) / "hldspec_skeptic_meta_review.json"
            meta_json.write_text(
                json.dumps(_meta_review_payload([_incomplete_cycle()])),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "scripts" / "review_runskeptic_evidence_quality.py"),
                    str(meta_json),
                    "--output-dir", tmpdir,
                    "--fail-on-rework",
                ],
                capture_output=True,
                cwd=str(repo_root),
            )
            self.assertEqual(2, result.returncode)

    def test_pass_review_exit_code_zero(self) -> None:
        """PASS review exits 0 even with --fail-on-rework."""
        import subprocess
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(__file__).parent.parent
            meta_json = Path(tmpdir) / "hldspec_skeptic_meta_review.json"
            meta_json.write_text(
                json.dumps(_meta_review_payload([_full_cycle()])),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "scripts" / "review_runskeptic_evidence_quality.py"),
                    str(meta_json),
                    "--output-dir", tmpdir,
                    "--fail-on-rework",
                ],
                capture_output=True,
                cwd=str(repo_root),
            )
            self.assertEqual(0, result.returncode)


class TestReadyGateWiresEvidenceQuality(unittest.TestCase):
    """Verify hldspec_ready_gate.py will run evidence quality check after meta review."""

    def test_ready_gate_references_evidence_quality_script(self) -> None:
        repo_root = Path(__file__).parent.parent
        content = (repo_root / "scripts" / "hldspec_ready_gate.py").read_text(encoding="utf-8")
        self.assertIn("review_runskeptic_evidence_quality", content)
        self.assertIn("fail-on-rework", content)

    def test_ready_gate_blocking_message_names_artifact_path(self) -> None:
        """Gate's failure message must reference the JSON artifact."""
        repo_root = Path(__file__).parent.parent
        content = (repo_root / "scripts" / "hldspec_ready_gate.py").read_text(encoding="utf-8")
        self.assertIn("meta_review_json", content)
        self.assertIn("REWORK_REQUIRED", content)


if __name__ == "__main__":
    unittest.main()
