from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_review(payload: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        source = root / "report.json"
        out = root / "out"
        source.write_text(json.dumps(payload), encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "review_runskeptic_evidence_quality.py"),
                str(source),
                "--output-dir",
                str(out),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        if result.returncode != 0:
            raise AssertionError(result.stderr + result.stdout)

        return json.loads((out / "runskeptic_evidence_quality_review.json").read_text(encoding="utf-8"))


class RunSkepticEvidenceQualityReviewTests(unittest.TestCase):
    def test_complete_runskeptic_cycle_passes(self) -> None:
        review = run_review(
            {
                "RunSkeptic_cycles": [
                    {
                        "decision": "FIX",
                        "recommendation": "KEEP_PLAN",
                        "observed_evidence": ["spec_build_plan.json plan_quality decision is FIX"],
                        "evidence_level": "observed",
                        "confidence": "adequate",
                        "unknowns": [],
                        "verification": "uv run python -m unittest discover -s tests -v",
                        "residual_risk": "none",
                    }
                ]
            }
        )

        self.assertEqual("PASS", review["status"])
        self.assertEqual(1, review["items_reviewed"])
        self.assertEqual([], review["findings"])

    def test_missing_observed_evidence_requires_rework(self) -> None:
        review = run_review(
            {
                "RunSkeptic_cycles": [
                    {
                        "decision": "FIX",
                        "recommendation": "KEEP_PLAN",
                        "evidence_level": "observed",
                        "confidence": "adequate",
                        "unknowns": [],
                        "verification": "tests passed",
                        "residual_risk": "none",
                    }
                ]
            }
        )

        self.assertEqual("REWORK_REQUIRED", review["status"])
        self.assertTrue(any(f["field"] == "observed_evidence" for f in review["findings"]))

    def test_unresolved_unknowns_require_human_review_when_complete(self) -> None:
        review = run_review(
            {
                "RunSkeptic_cycles": [
                    {
                        "decision": "FIX",
                        "recommendation": "REVIEW_PLAN",
                        "observed_evidence": "HLD-004 has unclear ownership.",
                        "evidence_level": "observed",
                        "confidence": "weak",
                        "unknowns": ["User must choose API owner."],
                        "verification": "rerun first_readonly after decision",
                        "residual_risk": "wrong owner could break dependency order",
                    }
                ]
            }
        )

        self.assertEqual("PENDING_HUMAN_REVIEW", review["status"])
        self.assertTrue(any(f["field"] == "unknowns" for f in review["findings"]))

    def test_nested_cycles_are_collected(self) -> None:
        review = run_review(
            {
                "plan_quality": {
                    "RunSkeptic_cycles": [
                        {
                            "decision": "DECOMPOSE",
                            "recommendation": "SPLIT_PLANNED_SPEC",
                            "observed_evidence": "API and processing in one planned spec.",
                            "evidence_level": "observed",
                            "confidence": {"confidence": "adequate"},
                            "unknowns": "none",
                            "verification": "plan quality fixture",
                            "residual_risk": "none",
                        }
                    ]
                }
            }
        )

        self.assertEqual("PASS", review["status"])
        self.assertEqual(1, review["items_reviewed"])


if __name__ == "__main__":
    unittest.main()
