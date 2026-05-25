"""Tests for constitution update plan generation from resolved option packets.

Key invariants:
- Only packets with affects_constitution=True produce entries.
- Unresolved packets (empty recommended_default) are skipped.
- human_approval_required is always True.
- Save/load roundtrip preserves all fields.
- HLDspec never writes constitution.md directly (test reads the comment).
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec.constitution_update_plan import (
    UpdatePlanEntry,
    build_update_plan,
    render_update_plan_md,
    save_update_plan,
)
from hldspec.option_packet import make_option_packet


def _constitution_packet(resolved: bool = True) -> object:
    return make_option_packet(
        "DEC-CONST-001",
        missing_fact="Gate ownership rule for workflow machines",
        options=["machine-owned", "shell-owned"],
        decision_type="source_of_truth",
        recommended_default="machine-owned" if resolved else "",
        affects_constitution=True,
        blast_radius="All gate machines",
        tradeoffs={"machine-owned": "Machines own all gate decisions; predictable."},
    )


def _non_constitution_packet() -> object:
    return make_option_packet(
        "DEC-NO-CONST",
        missing_fact="Which retry strategy?",
        options=["exponential", "linear"],
        decision_type="rollout_strategy",
        recommended_default="exponential",
        affects_constitution=False,
    )


class TestBuildUpdatePlan(unittest.TestCase):

    def test_affects_constitution_true_creates_entry(self):
        entries = build_update_plan([_constitution_packet(resolved=True)])
        self.assertEqual(1, len(entries))
        self.assertEqual("DEC-CONST-001", entries[0].decision_id)

    def test_affects_constitution_false_skipped(self):
        entries = build_update_plan([_non_constitution_packet()])
        self.assertEqual(0, len(entries))

    def test_unresolved_packet_skipped(self):
        entries = build_update_plan([_constitution_packet(resolved=False)])
        self.assertEqual(0, len(entries))

    def test_empty_packet_list_returns_empty(self):
        entries = build_update_plan([])
        self.assertEqual([], entries)

    def test_human_approval_always_required(self):
        entries = build_update_plan([_constitution_packet()])
        self.assertTrue(entries[0].human_approval_required)

    def test_current_rule_from_existing_rules(self):
        existing = {"DEC-CONST-001": "Machines gate only."}
        entries = build_update_plan([_constitution_packet()], existing_rules=existing)
        self.assertEqual("Machines gate only.", entries[0].current_rule)

    def test_current_rule_defaults_to_none_marker(self):
        entries = build_update_plan([_constitution_packet()])
        self.assertEqual("(none)", entries[0].current_rule)

    def test_proposed_rule_contains_decision(self):
        entries = build_update_plan([_constitution_packet()])
        self.assertIn("machine-owned", entries[0].proposed_rule)

    def test_why_comes_from_tradeoffs(self):
        entries = build_update_plan([_constitution_packet()])
        self.assertIn("Machines own all gate decisions", entries[0].why)

    def test_returns_update_plan_entry_type(self):
        entries = build_update_plan([_constitution_packet()])
        self.assertIsInstance(entries[0], UpdatePlanEntry)


class TestSaveUpdatePlan(unittest.TestCase):

    def test_save_creates_file(self):
        entries = build_update_plan([_constitution_packet()])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "constitution_update_plan.json"
            save_update_plan(entries, path)
            self.assertTrue(path.exists())

    def test_saved_file_has_schema_version(self):
        entries = build_update_plan([_constitution_packet()])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "constitution_update_plan.json"
            save_update_plan(entries, path)
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(1, data["schema_version"])

    def test_saved_file_requires_human_approval(self):
        entries = build_update_plan([_constitution_packet()])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "constitution_update_plan.json"
            save_update_plan(entries, path)
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(data["human_approval_required"])

    def test_note_says_never_edits_constitution_directly(self):
        entries = build_update_plan([_constitution_packet()])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "constitution_update_plan.json"
            save_update_plan(entries, path)
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("never edits", data["note"])
        self.assertIn("constitution.md", data["note"])


class TestRenderUpdatePlanMd(unittest.TestCase):

    def test_empty_entries_says_no_pending(self):
        md = render_update_plan_md([])
        self.assertIn("No constitution-impacting", md)

    def test_entry_decision_id_in_output(self):
        entries = build_update_plan([_constitution_packet()])
        md = render_update_plan_md(entries)
        self.assertIn("DEC-CONST-001", md)

    def test_human_approval_warning_present(self):
        md = render_update_plan_md(build_update_plan([_constitution_packet()]))
        self.assertIn("Human approval required", md)

    def test_never_edit_warning_present(self):
        md = render_update_plan_md([])
        self.assertIn("never edits", md)


if __name__ == "__main__":
    unittest.main()
