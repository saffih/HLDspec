from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_branch_queue_module():
    path = ROOT / "scripts" / "build_spec_branch_queue.py"
    spec = importlib.util.spec_from_file_location("build_spec_branch_queue", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


branch_queue = load_branch_queue_module()


class SpecBranchQueueTest(unittest.TestCase):
    def test_queue_is_blocked_when_work_order_not_allowed(self) -> None:
        result = branch_queue.build_branch_queue(
            {"allowed_to_write_workspace_specs": False, "items": [{"planned_spec_id": "001", "slug": "base"}]},
            Path("target_spec_work_order.json"),
        )

        self.assertEqual("BLOCKED_BY_WORK_ORDER", result["status"])
        self.assertIsNone(result["active_branch"])

    def test_queue_uses_active_first_branch_when_allowed(self) -> None:
        result = branch_queue.build_branch_queue(
            {
                "allowed_to_write_workspace_specs": True,
                "items": [{"order": 1, "planned_spec_id": "001", "slug": "base", "title": "Base"}],
            },
            Path("target_spec_work_order.json"),
        )

        self.assertEqual("READY", result["status"])
        self.assertEqual("001-base", result["active_branch"]["branch_name"])
        self.assertTrue(result["branch_policy"]["project_specs_write_requires_explicit_approval"])


if __name__ == "__main__":
    unittest.main()
