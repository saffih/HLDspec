from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TargetSpecWorkOrderTests(unittest.TestCase):
    def test_work_order_is_bottom_up_by_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)
            plan = {
                "plan_quality": {
                    "decision": "FIX",
                    "recommendation": "KEEP_PLAN",
                    "conflicts": [],
                },
                "planned_specs": [
                    {
                        "planned_spec_id": "018",
                        "slug": "018-http-api-design-and-endpoint-surface",
                        "title": "HTTP API Design and Endpoint Surface",
                        "source_hld_sections": ["HLD-018"],
                        "depends_on_specs": ["003", "007"],
                        "quality_flags": [],
                        "requires_user_review": False,
                    },
                    {
                        "planned_spec_id": "007",
                        "slug": "007-routing",
                        "title": "Routing",
                        "source_hld_sections": ["HLD-007"],
                        "depends_on_specs": ["003"],
                        "quality_flags": [],
                        "requires_user_review": False,
                    },
                    {
                        "planned_spec_id": "003",
                        "slug": "003-core-data",
                        "title": "Core Data",
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
                    str(ROOT / "scripts" / "build_target_spec_work_order.py"),
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
            work_order = json.loads((sync / "target_spec_work_order.json").read_text(encoding="utf-8"))
            self.assertEqual("READY", work_order["status"])
            self.assertEqual(["003", "007", "018"], [item["planned_spec_id"] for item in work_order["items"]])
            self.assertTrue(work_order["allowed_to_write_workspace_specs"])
            report = (sync / "target_spec_work_order.md").read_text(encoding="utf-8")
            self.assertIn("bottom-up topological order", report)
            self.assertIn("Do not jump to a nearby feature cluster", report)

    def test_work_order_blocks_when_plan_gate_not_green(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)
            plan = {
                "plan_quality": {
                    "decision": "DECOMPOSE",
                    "recommendation": "SPLIT_PLANNED_SPEC",
                    "conflicts": [],
                },
                "planned_specs": [
                    {
                        "planned_spec_id": "018",
                        "slug": "018-http-api",
                        "title": "HTTP API",
                        "source_hld_sections": ["HLD-018"],
                        "depends_on_specs": [],
                        "quality_flags": ["mixed_boundary"],
                        "requires_user_review": True,
                    }
                ],
            }
            plan_path = sync / "spec_build_plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_target_spec_work_order.py"),
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
            work_order = json.loads((sync / "target_spec_work_order.json").read_text(encoding="utf-8"))
            self.assertEqual("BLOCKED_BY_PLAN_GATE", work_order["status"])
            self.assertFalse(work_order["allowed_to_write_workspace_specs"])


if __name__ == "__main__":
    unittest.main()
