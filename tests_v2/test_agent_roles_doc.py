from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AgentRolesDocTests(unittest.TestCase):
    def test_agent_roles_doc_exists_and_defines_required_roles(self) -> None:
        text = (ROOT / "docs" / "HLDSPEC_V2_AGENT_ROLES.md").read_text(encoding="utf-8")

        required = [
            "Judge / Orchestrator Agent",
            "Raw HLD Scan Agent",
            "Architecture Reviewer Subagent",
            "Product Reviewer Subagent",
            "Governance Reviewer Subagent",
            "Interface Contract Reviewer Subagent",
            "Data / State Reviewer Subagent",
            "Security Reviewer Subagent",
            "Operations Reviewer Subagent",
            "RunSkeptic Reviewer Subagent",
            "Uncle Bob / SOLID Reviewer Subagent",
            "Handoff Docs Generator Agent",
            "SpecKit Readiness Judge Agent",
        ]

        for item in required:
            self.assertIn(item, text)

    def test_agent_roles_doc_defines_introspection_and_goal_match(self) -> None:
        text = (ROOT / "docs" / "HLDSPEC_V2_AGENT_ROLES.md").read_text(encoding="utf-8")

        required = [
            "Instruction-goal match:",
            "Did I only perform the role's stated goal?",
            "Did I use only the allowed input artifacts?",
            "Did every finding cite evidence?",
            "Did I distinguish evidence from inference?",
            "Did I stop at required human decisions?",
            "Did I preserve source-HLD safety?",
        ]

        for item in required:
            self.assertIn(item, text)

    def test_agent_roles_doc_defines_modes_and_production_rule(self) -> None:
        text = (ROOT / "docs" / "HLDSPEC_V2_AGENT_ROLES.md").read_text(encoding="utf-8")

        required = [
            "HLDSPEC_ROLE_REVIEWS=on",
            "HLDSPEC_ROLE_REVIEWS=local",
            "HLDSPEC_ROLE_REVIEWS=off",
            "Production rule",
            "architecture_review.json/md",
            "product_review.json/md",
            "governance_review.json/md",
            "role_review_summary.json/md",
        ]

        for item in required:
            self.assertIn(item, text)


if __name__ == "__main__":
    unittest.main()
