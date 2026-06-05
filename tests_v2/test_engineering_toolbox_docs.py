import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class EngineeringToolboxDocsTests(unittest.TestCase):
    def read(self, rel: str) -> str:
        return (ROOT / rel).read_text(encoding="utf-8")

    def assert_contains_all(self, text: str, phrases: tuple[str, ...]) -> None:
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_toolbox_links_to_anti_drift_contract(self):
        text = self.read("docs/ENGINEERING_TOOLBOX.md")
        self.assert_contains_all(
            text,
            (
                "docs/ANTI_DRIFT_CONTRACTS.md",
                "Contract 4",
                "must not weaken, remove, rename, or scatter",
            ),
        )

    def test_constitution_and_preferred_choice_split_is_documented(self):
        text = self.read("docs/ENGINEERING_TOOLBOX.md")
        self.assert_contains_all(
            text,
            (
                "Constitution candidates",
                "Preferred Choice Selection",
                "HLDspec must not silently overwrite the target constitution",
                "Preferred Choice Selection is target-specific guidance",
                "engineering_guidelines.md",
                "selection.json",
                "decisions.jsonl",
                "capability stewardship",
            ),
        )

    def test_minimal_engineering_guidelines_generation_is_implemented(self):
        text = self.read("docs/ENGINEERING_TOOLBOX.md")
        self.assert_contains_all(
            text,
            (
                "minimal P0 `engineering_guidelines.md` generation is implemented",
                "hldspec/engineering_selection.py",
                "SpeckitPreworkMachine",
                "validate_engineering_guidelines()",
                "hard prework gate",
                "P0-card selected guidance, not the full enforcement loop",
                "`selection.json` / `decisions.jsonl`",
                "must not copy the whole toolbox into every target",
            ),
        )

    def test_required_clean_software_cards_exist(self):
        text = self.read("docs/ENGINEERING_TOOLBOX.md")
        self.assert_contains_all(
            text,
            (
                "architecture.hexagonal_ports_adapters",
                "maintainability.capability_stewardship",
                "architecture.business_logic_container",
                "architecture.modular_boundaries",
                "testing.design_for_testability",
                "testing.business_logic_coverage",
                "testing.contract_boundary",
                "testing.ui_tester_skill",
                "environment.stage_safe_testing",
                "environment.prod_test_separation",
                "testing.resettable_fixtures",
            ),
        )

    def test_each_full_card_shape_is_required(self):
        text = self.read("docs/ENGINEERING_TOOLBOX.md")
        self.assert_contains_all(
            text,
            (
                "Trigger:",
                "Default choice:",
                "Required architecture shape:",
                "Required tests:",
                "Forbidden shortcuts:",
                "Evidence required:",
                "Constitution candidate:",
                "Preferred choice:",
            ),
        )

    def test_stage_safety_and_user_data_protection_are_explicit(self):
        text = self.read("docs/ENGINEERING_TOOLBOX.md")
        self.assert_contains_all(
            text,
            (
                "Feature work must not corrupt the user's active product or data",
                "Production or user-owned data requires explicit approval before mutation",
                "Test, stage, and production data/config must be separated",
                "No feature agent may run migrations, deletes, writes, imports, exports, or UI automation against production unless explicitly approved",
                "safe test/stage environment",
            ),
        )

    def test_business_logic_testability_is_explicit(self):
        text = self.read("docs/ENGINEERING_TOOLBOX.md")
        self.assert_contains_all(
            text,
            (
                "business logic container",
                "fully testable business logic container",
                "Every business rule must have focused unit/domain/application tests",
                "Handler/UI/E2E tests are not a substitute for business logic tests",
                "requiring a server/UI/database to test core rules",
            ),
        )

    def test_trigger_mapping_supports_future_selection(self):
        text = self.read("docs/ENGINEERING_TOOLBOX.md")
        self.assert_contains_all(
            text,
            (
                "`api_boundary`",
                "`cli_boundary`",
                "`ui_boundary`",
                "`persistence`",
                "`external_integration`",
                "`shared_mutable_data`",
                "`source_of_truth_ambiguity`",
                "`business_rules`",
                "`testability_risk`",
                "`stage_safe_testing_needed`",
                "`prod_test_separation_needed`",
                "`destructive_operation_risk`",
                "`migration_or_schema_change`",
                "`async_or_message_bus_candidate`",
                "`key_capability_added`",
            ),
        )

    def test_capability_stewardship_card_is_documented(self):
        text = self.read("docs/ENGINEERING_TOOLBOX.md")
        self.assert_contains_all(
            text,
            (
                "maintainability.capability_stewardship",
                "update the durable docs, tests, contracts, runbooks, and agent",
                "instructions that explain what changed",
                "what must not drift",
                "updated canonical doc, runbook, or backlog entry",
                "anti-drift or contract test",
            ),
        )

    def test_agents_reference_toolbox_and_anti_drift(self):
        for rel in ("AGENTS.md", "templates/orchestrator/AGENTS.md"):
            text = self.read(rel)
            self.assert_contains_all(
                text,
                (
                    "Engineering Toolbox",
                    "docs/ENGINEERING_TOOLBOX.md",
                    "docs/ANTI_DRIFT_CONTRACTS.md",
                    "engineering_guidelines.md",
                    "selected engineering guidance",
                    "New capability maintenance rule",
                    "tests that fail if the capability",
                ),
            )


if __name__ == "__main__":
    unittest.main()
