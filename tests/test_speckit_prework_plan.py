from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SpeckitPreworkPlanTests(unittest.TestCase):
    def test_builds_speckit_handoff_artifacts_without_writing_specs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)
            plan = {
                "plan_quality": {
                    "decision": "FIX",
                    "recommendation": "KEEP_PLAN",
                    "conflicts": [],
                    "findings": [],
                },
                "planned_specs": [
                    {
                        "planned_spec_id": "018",
                        "title": "HTTP API Design and Endpoint Surface",
                        "slug": "018-http-api-design-and-endpoint-surface",
                        "source_hld_sections": ["HLD-018"],
                        "depends_on_specs": ["003"],
                        "quality_flags": [],
                        "requires_user_review": False,
                    },
                    {
                        "planned_spec_id": "003",
                        "title": "Core Shared State Model",
                        "slug": "003-core-shared-state-model",
                        "source_hld_sections": ["HLD-003"],
                        "depends_on_specs": [],
                        "quality_flags": [],
                        "requires_user_review": False,
                    },
                ],
            }
            plan_path = sync / "spec_build_plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_speckit_prework_plan.py"),
                    str(plan_path),
                    str(workspace),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)

            for name in [
                "speckit_input_manifest",
                "speckit_invocation_queue",
                "constitution_update_plan",
                "feature_dependency_graph",
            ]:
                self.assertTrue((sync / f"{name}.json").exists())
                self.assertTrue((sync / f"{name}.md").exists())

            queue = json.loads((sync / "speckit_invocation_queue.json").read_text(encoding="utf-8"))
            self.assertEqual("PENDING_HUMAN_PLAN_APPROVAL", queue["status"])
            self.assertEqual("003", queue["items"][0]["feature_id"])
            self.assertEqual("/speckit.specify", queue["items"][0]["speckit_command"])

            constitution = json.loads((sync / "constitution_update_plan.json").read_text(encoding="utf-8"))
            self.assertEqual("TBD", constitution["human_checkpoint"]["human_decision"])
            self.assertIn("ARCH-002", [rule["rule_id"] for rule in constitution["required_rules"]])

            manifest = (sync / "speckit_input_manifest.md").read_text(encoding="utf-8")
            self.assertIn("SpecKit owns final generated feature artifacts", manifest)
            self.assertIn("SPLIT_API_CONTRACT_FROM_PROCESSING", manifest)


if __name__ == "__main__":
    unittest.main()
