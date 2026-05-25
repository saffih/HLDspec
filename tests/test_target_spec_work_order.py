from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_work_order_module():
    path = ROOT / "scripts" / "build_target_spec_work_order.py"
    spec = importlib.util.spec_from_file_location("build_target_spec_work_order", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


work_order = load_work_order_module()


class TargetSpecWorkOrderTest(unittest.TestCase):
    def test_work_order_blocks_when_plan_gate_is_not_green(self) -> None:
        plan = {
            "plan_quality": {"decision": "DECOMPOSE", "recommendation": "SPLIT_PLANNED_SPEC", "conflicts": []},
            "planned_specs": [{"planned_spec_id": "002", "slug": "second"}, {"planned_spec_id": "001", "slug": "first"}],
        }

        result = work_order.build_work_order(plan, Path("spec_build_plan.json"))

        self.assertEqual("BLOCKED_BY_PLAN_GATE", result["status"])
        self.assertFalse(result["allowed_to_write_workspace_specs"])
        self.assertTrue(result["requires_human_write_approval"])

    def test_work_order_orders_dependencies_before_dependents(self) -> None:
        plan = {
            "plan_quality": {"decision": "PASS", "recommendation": "KEEP_PLAN", "conflicts": []},
            "planned_specs": [
                {"planned_spec_id": "002", "slug": "child", "depends_on_specs": ["001"]},
                {"planned_spec_id": "001", "slug": "base", "depends_on_specs": []},
            ],
        }

        result = work_order.build_work_order(plan, Path("spec_build_plan.json"))

        self.assertEqual("READY", result["status"])
        self.assertEqual(["001", "002"], [item["planned_spec_id"] for item in result["items"]])


if __name__ == "__main__":
    unittest.main()
