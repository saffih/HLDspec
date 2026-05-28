import unittest
from pathlib import Path

from hldspec import implementation_slicing as slicing

ROOT = Path(__file__).resolve().parents[1]


SLICE_ARTIFACT_FILENAMES = (
    slicing.IMPLEMENTATION_SLICING_POLICY_FILE,
    slicing.IMPLEMENTATION_SLICES_FILE,
    slicing.SLICE_TEST_POLICY_FILE,
    slicing.SPECKIT_SLICE_EXECUTION_PROMPT_FILE,
    slicing.ANCHOR_COVERAGE_SCHEMA_FILE,
)


class ArtifactContractDocsTests(unittest.TestCase):
    def read(self, rel: str) -> str:
        return (ROOT / rel).read_text(encoding="utf-8")

    def test_contract_style_doc_has_required_shape(self):
        text = self.read("docs/HLDSPEC_ARTIFACT_CONTRACT_STYLE.md")
        for phrase in (
            "Purpose",
            "Inputs",
            "Authority",
            "Allowed sources",
            "Allowed actions",
            "Forbidden actions",
            "Expected outputs",
            "Validation required",
            "Stop conditions",
            "Report format",
            "Next owner",
            "Evidence",
        ):
            self.assertIn(phrase, text)

    def test_readme_points_to_artifact_contract_style(self):
        text = self.read("README.md")
        self.assertIn("HLDSPEC_ARTIFACT_CONTRACT_STYLE.md", text)
        # Whitespace-normalised so the phrase matches regardless of line wrapping.
        normalized = " ".join(text.lower().split())
        self.assertIn("inputs, authority, allowed actions, forbidden actions", normalized)

    def test_slice_doc_uses_slice_card_shape(self):
        text = self.read("docs/SPECKIT_SLICE_CONTROL.md")
        self.assertIn("Slice card", text)
        self.assertIn("Allowed work", text)
        self.assertIn("Forbidden work", text)
        self.assertIn("Focused tests", text)
        self.assertIn("Regression tests", text)
        for filename in SLICE_ARTIFACT_FILENAMES:
            self.assertIn(filename, text)

    def test_gap_handoff_template_uses_contract_shape(self):
        text = self.read("docs/HLDSPEC_GAP_HANDOFF_TEMPLATE.md")
        for phrase in (
            "Current state",
            "Known gaps",
            "What was tested",
            "What was not tested",
            "Next safe patch",
            "Forbidden actions",
            "Validation required",
        ):
            self.assertIn(phrase, text)

    def test_agent_instructions_require_contract_shape(self):
        root_agents = self.read("AGENTS.md")
        target_agents = self.read("templates/orchestrator/AGENTS.md")
        for text in (root_agents, target_agents):
            self.assertIn("artifact contract", text.lower())
            self.assertIn("Inputs", text)
            self.assertIn("Stop Conditions", text)
            for filename in SLICE_ARTIFACT_FILENAMES:
                self.assertIn(filename, text)

    def test_docs_index_has_no_duplicate_development_handoff_row(self):
        text = self.read("docs/DOCS_INDEX.md")
        handoff_rows = [line for line in text.splitlines() if "HLDSPEC_DEVELOPMENT_HANDOFF.md" in line]
        self.assertEqual(len(handoff_rows), 1)
        for filename in (
            "../README.md",
            "SPECKIT_SLICE_CONTROL.md",
            "SPECKIT_PROXY_PROTOCOL.md",
            "HLDSPEC_GAP_HANDOFF_TEMPLATE.md",
        ):
            self.assertIn(filename, text)


if __name__ == "__main__":
    unittest.main()
