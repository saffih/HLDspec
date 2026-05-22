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
        source = root / "plan.json"
        out = root / "out"
        source.write_text(json.dumps(payload), encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "review_constitution_rule_quality.py"),
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

        return json.loads((out / "constitution_rule_quality_review.json").read_text(encoding="utf-8"))


class ConstitutionRuleQualityReviewTests(unittest.TestCase):
    def test_complete_constitution_rule_passes(self) -> None:
        review = run_review(
            {
                "constitution_rules": [
                    {
                        "rule": "Data ownership must be defined before API specs depend on it.",
                        "rationale": "Prevents API contracts from freezing unstable state ownership.",
                        "hld_evidence": ["HLD-003 data state model", "HLD-004 API contract"],
                        "violation_example": "Creating the API spec before defining the persisted state owner.",
                        "speckit_phase_enforced": "specify",
                        "affected_artifacts": ["constitution.md", "spec.md", "plan.md"],
                        "open_question": "none",
                    }
                ]
            }
        )

        self.assertEqual("PASS", review["status"])
        self.assertEqual(1, review["rules_reviewed"])
        self.assertEqual([], review["findings"])

    def test_generic_string_rule_requires_rework(self) -> None:
        review = run_review(
            {
                "required_constitution_rules": [
                    "HLD.md is the design source of truth.",
                ]
            }
        )

        self.assertEqual("REWORK_REQUIRED", review["status"])
        fields = {finding["field"] for finding in review["findings"]}
        self.assertIn("hld_evidence", fields)
        self.assertIn("rationale", fields)
        self.assertIn("violation_example", fields)

    def test_missing_hld_evidence_is_blocker(self) -> None:
        review = run_review(
            {
                "constitution_rules": [
                    {
                        "rule": "API specs must follow dependency order.",
                        "rationale": "Avoids specifying consumers before foundations.",
                        "hld_evidence": "",
                        "violation_example": "API generated before state model.",
                        "speckit_phase_enforced": "specify",
                        "affected_artifacts": ["spec.md"],
                        "open_question": "none",
                    }
                ]
            }
        )

        self.assertEqual("REWORK_REQUIRED", review["status"])
        self.assertTrue(any(finding["severity"] == "BLOCKER" for finding in review["findings"]))

    def test_open_question_requires_human_review_when_rule_is_complete(self) -> None:
        review = run_review(
            {
                "constitution_rules": [
                    {
                        "rule": "The first feature must be dependency-free.",
                        "rationale": "SpecKit should start from a foundation.",
                        "hld_evidence": "HLD-001 foundation has no DEPENDS REF.",
                        "violation_example": "Starting with HLD-004 before HLD-001.",
                        "speckit_phase_enforced": "specify",
                        "affected_artifacts": ["speckit_invocation_queue.md"],
                        "open_question": "Should HLD-001 be the first feature?",
                    }
                ]
            }
        )

        self.assertEqual("PENDING_HUMAN_REVIEW", review["status"])
        self.assertTrue(any(finding["field"] == "open_question" for finding in review["findings"]))


if __name__ == "__main__":
    unittest.main()
