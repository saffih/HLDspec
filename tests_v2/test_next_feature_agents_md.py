from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hldspec import next_feature_agents_md as nfa


class NextFeatureAgentsMdTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-next-feature-agents-")
        self.target = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_bootstrap_states_the_canonical_chain(self) -> None:
        text = nfa.build_next_feature_agents_md(self.target)
        self.assertIn(
            "CONSTITUTION → SPECIFY → CLARIFY → PLAN → CHECKLIST → TASKS → ANALYZE → IMPLEMENT",
            text,
        )

    def test_bootstrap_carries_the_hard_safety_rules(self) -> None:
        text = nfa.build_next_feature_agents_md(self.target)
        # Drives, never executes/merges.
        self.assertIn("Never", text)
        self.assertIn("merge", text.lower())
        self.assertIn("one step at a time", text.lower())
        self.assertIn("scripts/next_feature_readiness_report.py", text)
        # SpecKit owns generation; agent never writes specs/code.
        self.assertIn("SpecKit", text)

    def test_bootstrap_frames_journey_3_as_target_repo_run_card_loop(self) -> None:
        text = nfa.build_next_feature_agents_md(self.target)
        self.assertIn("operating in this target repo", text)
        self.assertIn("SpecKit run card", text)
        self.assertIn("recommended_model", text)
        self.assertIn("do_not_run_yet", text)
        self.assertIn("report_back", text)
        self.assertIn("Do **not** create branches yourself", text)
        self.assertIn("/speckit.specify", text)

    def test_snapshot_included_when_report_given(self) -> None:
        report = {"phase": "READY_FOR_PLAN", "speckit_next_action": "/speckit.plan"}
        text = nfa.build_next_feature_agents_md(self.target, report)
        self.assertIn("READY_FOR_PLAN", text)
        self.assertIn("/speckit.plan", text)

    def test_write_places_bootstrap_in_sync_dir_and_is_idempotent(self) -> None:
        first = nfa.write_next_feature_agents_md(self.target)
        path = Path(first["agents_md"])
        self.assertTrue(path.is_file())
        self.assertEqual(nfa.BOOTSTRAP_FILE, path.name)
        before = path.read_text(encoding="utf-8")
        second = nfa.write_next_feature_agents_md(self.target)
        self.assertEqual(first, second)
        self.assertEqual(before, path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
