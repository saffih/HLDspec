from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ContextTailoringComplianceReviewTests(unittest.TestCase):
    def test_review_generates_read_only_report(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "review_context_tailoring_compliance.py"),
                    "--repo",
                    str(ROOT),
                    "--output-dir",
                    str(out),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            data = json.loads((out / "context_tailoring_compliance_review.json").read_text(encoding="utf-8"))
            self.assertEqual("CONTEXT_TAILORING_COMPLIANCE_REVIEW", data["review_type"])
            self.assertIn(data["status"], {"PASS", "ACTIONS_FOUND", "CONFLICTS_FOUND"})
            self.assertGreaterEqual(data["summary"]["total_findings"], 10)

            first = data["findings"][0]
            for key in ["finding_id", "rule", "artifact", "decision", "recommendation", "evidence", "issue_type"]:
                self.assertIn(key, first)

            md = (out / "context_tailoring_compliance_review.md").read_text(encoding="utf-8")
            self.assertIn("Context Tailoring Compliance Review", md)
            self.assertIn("Allowed context", md)
            self.assertIn("Findings", md)

    def test_agents_declares_current_state_entry_points_and_legacy_artifacts(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("hldspec_state.md", text)
        self.assertIn("speckit_prework_package.md", text)
        self.assertIn("Legacy/supporting when SpecKit is available", text)
        self.assertNotIn("report whether target-spec generation is allowed", text)


if __name__ == "__main__":
    unittest.main()
