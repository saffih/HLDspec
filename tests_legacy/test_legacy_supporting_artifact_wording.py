from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LegacySupportingArtifactWordingTests(unittest.TestCase):
    def test_target_work_order_is_marked_legacy_supporting(self) -> None:
        text = (ROOT / "scripts" / "build_target_spec_work_order.py").read_text(encoding="utf-8")
        self.assertIn("Legacy/supporting when SpecKit is available", text)
        self.assertIn("not the controlling handoff", text)
        self.assertIn("speckit_prework_package.md", text)

    def test_spec_branch_queue_is_marked_legacy_supporting(self) -> None:
        text = (ROOT / "scripts" / "build_spec_branch_queue.py").read_text(encoding="utf-8")
        self.assertIn("Legacy/supporting when SpecKit is available", text)
        self.assertIn("not the controlling handoff", text)
        self.assertIn("speckit_invocation_queue.md", text)

    def test_canonical_flow_defines_legacy_supporting_rule(self) -> None:
        text = (ROOT / "docs" / "CANONICAL_FLOW.md").read_text(encoding="utf-8")
        self.assertIn("Legacy/supporting when SpecKit is available", text)
        self.assertIn("target_spec_work_order", text)
        self.assertIn("spec_branch_queue", text)

    def test_primary_user_entry_points_remain_state_and_package(self) -> None:
        project = (ROOT / "scripts" / "project_continue.sh").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("hldspec_state.md", project)
        self.assertIn("speckit_prework_package.md", project)
        self.assertIn("hldspec_state.md", agents)
        self.assertIn("speckit_prework_package.md", agents)


if __name__ == "__main__":
    unittest.main()
