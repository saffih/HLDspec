from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SpecBranchQueueTests(unittest.TestCase):
    def test_branch_queue_is_one_at_a_time_and_uses_work_order(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)

            work_order = {
                "status": "READY",
                "allowed_to_write_workspace_specs": True,
                "ordering_rule": "bottom-up topological order by depends_on_specs",
                "items": [
                    {
                        "order": 1,
                        "planned_spec_id": "003",
                        "slug": "003-core-data",
                        "title": "Core Data",
                        "target_workspace_path": "specs/003-core-data/spec.md",
                        "source_hld_sections": ["HLD-003"],
                        "depends_on_specs": [],
                    },
                    {
                        "order": 2,
                        "planned_spec_id": "018",
                        "slug": "018-http-api-design-and-endpoint-surface",
                        "title": "HTTP API Design and Endpoint Surface",
                        "target_workspace_path": "specs/018-http-api-design-and-endpoint-surface/spec.md",
                        "source_hld_sections": ["HLD-018"],
                        "depends_on_specs": ["003"],
                    },
                ],
            }
            path = sync / "target_spec_work_order.json"
            path.write_text(json.dumps(work_order), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_spec_branch_queue.py"),
                    str(path),
                    str(workspace),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            queue = json.loads((sync / "spec_branch_queue.json").read_text(encoding="utf-8"))
            self.assertEqual("READY", queue["status"])
            self.assertEqual("ONE_SPEC_BRANCH_AT_A_TIME", queue["execution_mode"])
            self.assertEqual("003", queue["active_branch"]["planned_spec_id"])
            self.assertEqual("003-core-data", queue["active_branch"]["branch_name"])
            self.assertTrue(queue["branch_policy"]["branch_oriented"])
            self.assertFalse(queue["branch_policy"]["create_branches_automatically"])

            report = (sync / "spec_branch_queue.md").read_text(encoding="utf-8")
            self.assertIn("Spec Kit work is branch-oriented", report)
            self.assertIn("process only the active next branch", report)

    def test_branch_queue_blocks_when_work_order_not_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)

            work_order = {
                "status": "BLOCKED_BY_PLAN_GATE",
                "allowed_to_write_workspace_specs": False,
                "items": [
                    {
                        "order": 1,
                        "planned_spec_id": "018",
                        "slug": "018-http-api",
                        "title": "HTTP API",
                        "target_workspace_path": "specs/018-http-api/spec.md",
                    }
                ],
            }
            path = sync / "target_spec_work_order.json"
            path.write_text(json.dumps(work_order), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_spec_branch_queue.py"),
                    str(path),
                    str(workspace),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            queue = json.loads((sync / "spec_branch_queue.json").read_text(encoding="utf-8"))
            self.assertEqual("BLOCKED_BY_WORK_ORDER", queue["status"])
            self.assertIsNone(queue["active_branch"])


if __name__ == "__main__":
    unittest.main()
