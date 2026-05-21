from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SpeckitPreworkQualityReviewTests(unittest.TestCase):
    def test_quality_review_presents_case_and_first_feature(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)

            (sync / "speckit_input_manifest.json").write_text(
                json.dumps(
                    {
                        "features": [
                            {
                                "feature_id": "001",
                                "feature_name": "Rock Foundation",
                                "depends_on_features": [],
                                "speckit_specify_input": "Build the rock foundation.",
                                "decomposition_flags": [],
                            },
                            {
                                "feature_id": "002",
                                "feature_name": "HTTP API Surface",
                                "depends_on_features": ["001"],
                                "speckit_specify_input": "Build HTTP API surface.",
                                "decomposition_flags": ["SPLIT_API_CONTRACT_FROM_PROCESSING"],
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (sync / "feature_dependency_graph.json").write_text(
                json.dumps({"bottom_up_order": ["001", "002"], "edges": [{"from": "001", "to": "002"}]}),
                encoding="utf-8",
            )
            (sync / "constitution_update_plan.json").write_text(
                json.dumps(
                    {
                        "required_rules": [
                            {"rule_id": "ARCH-001", "name": "HLD Architecture Source of Truth"},
                            {"rule_id": "ARCH-002", "name": "API Contract and Processing Separation"},
                        ],
                        "human_checkpoint": {"human_decision": "TBD"},
                    }
                ),
                encoding="utf-8",
            )
            (sync / "speckit_invocation_queue.json").write_text(
                json.dumps(
                    {
                        "items": [
                            {"feature_id": "001", "feature_name": "Rock Foundation"},
                            {"feature_id": "002", "feature_name": "HTTP API Surface"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_speckit_prework_quality_review.py"),
                    str(workspace),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)

            review = json.loads((sync / "speckit_prework_quality_review.json").read_text(encoding="utf-8"))
            self.assertEqual("APPROVAL_READY_WITH_ACTIONS", review["status"])
            self.assertEqual("001", review["case_to_present"]["first_feature_case"]["feature_id"])
            self.assertIn("no dependencies", review["case_to_present"]["first_feature_case"]["why_first"])
            self.assertEqual("TBD", review["human_checkpoint"]["human_decision"])

            report = (sync / "speckit_prework_quality_review.md").read_text(encoding="utf-8")
            self.assertIn("Constitution case", report)
            self.assertIn("Architecture and dependency case", report)
            self.assertIn("First feature case", report)
            self.assertIn("Beskeptic findings", report)
            self.assertIn("The judge/orchestrator must rebuild affected artifacts", report)


if __name__ == "__main__":
    unittest.main()
