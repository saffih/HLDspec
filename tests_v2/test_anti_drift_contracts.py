import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AntiDriftContractTests(unittest.TestCase):
    def read(self, rel: str) -> str:
        return (ROOT / rel).read_text(encoding="utf-8")

    def assert_contains_all(self, text: str, phrases: tuple[str, ...]) -> None:
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_anti_drift_doc_exists_and_names_four_contracts(self):
        text = self.read("docs/ANTI_DRIFT_CONTRACTS.md")
        self.assert_contains_all(
            text,
            (
                "Product model contract",
                "Source-truth and SpecKit ownership contract",
                "Slice, mediator, and implementation guidance contract",
                "Engineering Toolbox contract",
            ),
        )

    def test_product_model_contract_is_protected(self):
        text = self.read("docs/ANTI_DRIFT_CONTRACTS.md")
        self.assert_contains_all(
            text,
            (
                "agent-first control layer around HLD-driven SpecKit work",
                "HLD Authoring",
                "SpecKit Preparation",
                "Implementation Guidance",
                "SpecKit Preparation is the core product",
                "HLDspec does not replace SpecKit",
                "HLDspec does not implement the target product by itself",
            ),
        )

    def test_source_truth_and_speckit_ownership_contract_is_protected(self):
        text = self.read("docs/ANTI_DRIFT_CONTRACTS.md")
        self.assert_contains_all(
            text,
            (
                "The HLD remains the product source of truth",
                ".hldspec/source_package/",
                ".specify/source/",
                "generated read-only mirror",
                "real `.specify/` workspace is SpecKit-owned",
                "HLDspec must not fake a SpecKit workspace",
            ),
        )

    def test_slice_mediator_and_guidance_contract_is_protected(self):
        text = self.read("docs/ANTI_DRIFT_CONTRACTS.md")
        self.assert_contains_all(
            text,
            (
                "Operator / Doctor / Devin Mediator Boundary",
                "HLDspec Operator is HLDspec core behavior",
                "SpecKit Doctor is the diagnostic/preflight part of the SpecKit Operator",
                "SpecKit Doctor is not the whole Operator",
                "SpecKit Operator is broader than Doctor",
                "planned next layer is lifecycle state and next-safe-action guidance",
                "Until Operator State exists, Doctor provides readiness/preflight facts only and must not pretend to decide the full lifecycle",
                "Devin Mediator is a Devin-specific runtime adapter",
                "Devin Mediator is not HLDspec core behavior",
                "HLDspec does not mediate Devin directly",
                "Devin Mediator consumes HLDspec Operator facts/artifacts to drive Devin safely",
                "Devin-specific exact go/stop/session rules must not define the generic Operator layer",
                "Operator / Doctor / Devin Mediator are not interchangeable names for the same thing",
                "specify -> plan -> tasks -> analyze",
                "many guided implementation slices",
                "HLDspec provides and bounds slice-control",
                "user or Agent Mediator enforces slice scope during runtime",
                "Agent Mediator is not the Implementation Agent",
                "Tmux or session state is visibility only",
                "Do not let Doctor readiness be treated as full lifecycle operation",
            ),
        )

    def test_engineering_toolbox_contract_is_protected(self):
        text = self.read("docs/ANTI_DRIFT_CONTRACTS.md")
        self.assert_contains_all(
            text,
            (
                "Engineering Toolbox is durable engineering doctrine",
                "Constitution candidates",
                "Preferred Choice Selection",
                "selection.json",
                "decisions.jsonl",
                "engineering_guidelines.md",
            ),
        )

    def test_non_droppable_engineering_concepts_are_named(self):
        text = self.read("docs/ANTI_DRIFT_CONTRACTS.md").lower()
        for phrase in (
            "hexagonal architecture",
            "ports and adapters",
            "business logic container",
            "design for testability",
            "business logic coverage",
            "contract and boundary testing",
            "ui tester skill",
            "stage-safe testing",
            "prod/test separation",
            "resettable fixtures",
            "source-of-truth ownership",
            "safe test/stage environment",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_docs_index_lists_anti_drift_and_toolbox(self):
        text = self.read("docs/DOCS_INDEX.md")
        self.assertIn("ANTI_DRIFT_CONTRACTS.md", text)
        self.assertIn("ENGINEERING_TOOLBOX.md", text)


if __name__ == "__main__":
    unittest.main()
