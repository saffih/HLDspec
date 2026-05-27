import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class HldspecConceptDocsTests(unittest.TestCase):
    def read(self, rel: str) -> str:
        return (ROOT / rel).read_text(encoding="utf-8")

    def test_readme_is_conceptual_front_door(self):
        text = self.read("README.md")
        for phrase in (
            "HLDspec is an agent-first control layer",
            "The HLD remains the source of truth. The implementation is sliced, not the truth.",
            "## Conceptual flow",
            "```mermaid",
            "## Slice-controlled implementation",
            "One complete HLD",
            "Many approved implementation slices",
            "docs/SPECKIT_SLICE_CONTROL.md",
            "docs/HLDSPEC_GAP_HANDOFF_TEMPLATE.md",
        ):
            self.assertIn(phrase, text)

    def test_slice_control_doc_defines_required_slices_and_phase_behavior(self):
        text = self.read("docs/SPECKIT_SLICE_CONTROL.md")
        for phrase in (
            "Do not split the HLD to make smaller specs.",
            "SpecKit plans the whole product once. HLDspec controls implementation slice by slice.",
            "### FOUNDATION",
            "### WALKING_SKELETON",
            "### DOMAIN_MODEL",
            "### CONTRACTS",
            "### BUSINESS_LOGIC",
            "### PERSISTENCE",
            "### API",
            "### CLI",
            "### UI",
            "### INTEGRATION_HARDENING",
            "### specify",
            "### plan",
            "### tasks",
            "### analyze",
            "### implement",
            "focused tests pass",
            "prior-slice regression passes",
        ):
            self.assertIn(phrase, text)

    def test_gap_handoff_template_is_status_not_truth(self):
        text = self.read("docs/HLDSPEC_GAP_HANDOFF_TEMPLATE.md")
        for phrase in (
            "A gap handoff is a status and continuation artifact.",
            "It is not architecture",
            "## Current state",
            "## Known gaps",
            "## Next safe patch",
            "## Validation required",
            "Do not claim tests passed unless exact commands ran.",
        ):
            self.assertIn(phrase, text)

    def test_agent_docs_reference_slice_and_gap_handoff_rules(self):
        root_agents = self.read("AGENTS.md")
        orchestrator_agents = self.read("templates/orchestrator/AGENTS.md")
        for text in (root_agents, orchestrator_agents):
            self.assertIn("SpecKit slice-control rule", text)
            self.assertIn("docs/SPECKIT_SLICE_CONTROL.md", text)
            self.assertIn("docs/HLDSPEC_GAP_HANDOFF_TEMPLATE.md", text)
            self.assertIn("one complete specify -> plan -> tasks -> analyze flow", text)

    def test_docs_index_points_to_front_door_and_slice_docs(self):
        text = self.read("docs/DOCS_INDEX.md")
        for phrase in (
            "../README.md",
            "SPECKIT_SLICE_CONTROL.md",
            "HLDSPEC_GAP_HANDOFF_TEMPLATE.md",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
