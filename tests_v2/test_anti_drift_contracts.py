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
                "SOURCE_PACKAGE_READY",
                "INIT_PREREQS_READY",
                "WORKSPACE_INITIALIZED",
                "MIRROR_SYNCED",
                "READY_FOR_SPECIFY",
                "BUILD_LOOP_ACTIVE",
                "post-init mirror sync",
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
                "HLDspec Operator includes readiness-first Operator State that gates the readiness boundary and reports post-readiness SpecKit lifecycle evidence when phase artifacts exist",
                "HLDspec Operator uses target facts, source-package state, Engineering Toolbox guidance, implementation slicing, mediator/operator guidance, and SpecKit Doctor readiness facts today",
                "Richer post-implementation reassessment remains planned",
                "Doctor remains readiness/preflight only and must not decide the full lifecycle",
                "Devin Mediator is a Devin-specific runtime adapter",
                "Devin Mediator is not HLDspec core behavior",
                "HLDspec does not mediate Devin directly",
                "HLDspec produces operator facts, source-package state/context, Engineering Toolbox guidance, implementation slicing, mediator/operator guidance, SpecKit Doctor readiness facts, and readiness-first lifecycle Operator State today",
                "Operator State must continue to surface post-readiness lifecycle states such as `PLAN_ACTIVE`, `TASKS_ACTIVE`, `ANALYZE_READY`, and `REASSESSMENT_REQUIRED`",
                "Richer post-implementation reassessment is future work, not already fully implemented",
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
        self.assertNotIn("HLDspec produces operator facts, lifecycle state, and next-safe-action guidance", text)
        self.assertNotIn("next-safe-action guidance today", text)
        self.assertNotIn("Until Operator State exists", text)

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
                "SpecKit prework approval",
                "missing or invalid",
                "SpeckitPreworkMachine",
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
