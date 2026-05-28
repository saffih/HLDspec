import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_doc(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class MediatorJourney3DocsTests(unittest.TestCase):
    def test_terminology_defines_journey3_mediator_skill_contract(self):
        text = read_doc("docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md")

        required = [
            "Journey 3 mediator skill contract",
            "create agent on {path} as {session-name} using model {model} [permission-mode {mode}]",
            "Devin mediator skill",
            "Codex / Claude direct mediator",
            "target/.hldspec/source_package/",
            "engineering_guidelines.md",
            "implementation_slices.json",
            "slice_test_policy.md",
            "speckit_slice_execution_prompt.md",
            "explicitly says `go`",
            "`stop` and `stop now` dominate",
            "`rerun tests`, `clarify`, or `reassess`",
        ]

        for item in required:
            with self.subTest(item=item):
                self.assertIn(item, text)

    def test_mediator_protocol_defines_devin_activation_and_direct_mode(self):
        text = read_doc("docs/MEDIATOR_PROMPT_PROTOCOL.md")

        required = [
            "Devin mediator activation",
            "create agent on {path} as {session-name} using model {model} [permission-mode {mode}]",
            "devin mediator",
            "Required mediator inputs",
            "target/.hldspec/source_package/",
            "target/.specify/source/",
            "target/specs/",
            "Codex / Claude direct mediator mode",
            "User != Agent Mediator != Implementation Agent",
            "tmux/session output != approval state",
            "failed tests != completion",
            "scope expansion != allowed work",
            "go",
            "stop",
            "clarify",
            "rerun tests",
            "reassess",
        ]

        for item in required:
            with self.subTest(item=item):
                self.assertIn(item, text)

    def test_anti_drift_protects_mediator_contract(self):
        text = read_doc("docs/ANTI_DRIFT_CONTRACTS.md")

        required = [
            "go",
            "stop",
            "stop now",
            "clarify",
            "rerun tests",
            "reassess",
            "create agent on {path} as {session-name} using model {model} [permission-mode {mode}]",
            "Codex and Claude may use direct mediator mode",
            "Do not remove or weaken the Devin mediator activation syntax",
            "failed tests, missing evidence, or scope expansion",
        ]

        for item in required:
            with self.subTest(item=item):
                self.assertIn(item, text)


if __name__ == "__main__":
    unittest.main()
