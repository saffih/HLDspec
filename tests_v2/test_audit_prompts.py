from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "templates" / "audit"
PLAN = AUDIT_DIR / "AUDIT_PLAN_PROMPT.md"
CONSOLIDATE = AUDIT_DIR / "AUDIT_CONSOLIDATE_PROMPT.md"
CANONICAL = ROOT / "docs" / "HLDSPEC_TERMINOLOGY_AND_FLOW.md"


class AuditPromptContractTests(unittest.TestCase):
    def test_templates_exist(self) -> None:
        self.assertTrue(PLAN.is_file(), str(PLAN))
        self.assertTrue(CONSOLIDATE.is_file(), str(CONSOLIDATE))

    def test_plan_prompt_is_read_only_and_in_session(self) -> None:
        text = PLAN.read_text(encoding="utf-8")
        self.assertIn("READ-ONLY", text)
        self.assertIn("Do not modify, create, or delete any file", text)
        self.assertIn("your session reply, not a file", text)

    def test_plan_prompt_defines_terminology_and_evidence_levels(self) -> None:
        text = PLAN.read_text(encoding="utf-8")
        for term in ("Audit Report", "Finding", "Action Item", "Work Order", "Unverified Claim"):
            self.assertIn(term, text, term)
        for level in ("OBSERVED", "REPRODUCED", "HISTORICAL", "INFERRED"):
            self.assertIn(level, text, level)
        self.assertIn("Not examined", text)
        self.assertIn("acceptance check", text)

    def test_plan_prompt_emits_next_step_prompts(self) -> None:
        text = PLAN.read_text(encoding="utf-8")
        self.assertIn("ready-to-paste prompt", text)
        self.assertIn("Scan step contract", text)

    def test_consolidate_prompt_merges_without_inventing(self) -> None:
        text = CONSOLIDATE.read_text(encoding="utf-8")
        self.assertIn("READ-ONLY", text)
        self.assertIn("add no new findings", text)
        self.assertIn("Never upgrade INFERRED", text)
        self.assertIn("Work Orders", text)
        self.assertIn("Not examined", text)

    def test_canonical_doc_defines_audit_trigger(self) -> None:
        text = CANONICAL.read_text(encoding="utf-8")
        self.assertIn("`audit project`", text)
        self.assertIn("`scan for gaps`", text)
        self.assertIn("templates/audit/", text)
        self.assertIn("`HLDspec help audit project`", text)
        self.assertIn("never auto-executes its own Work Orders", text)


if __name__ == "__main__":
    unittest.main()
