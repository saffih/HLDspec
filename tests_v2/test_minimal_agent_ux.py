from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MinimalAgentUXTests(unittest.TestCase):
    def setUp(self) -> None:
        self.doc = (ROOT / "docs" / "HLDSPEC_MINIMAL_AGENT_UX.md").read_text(encoding="utf-8")
        self.agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    def test_minimal_agent_ux_doc_exists_and_defines_short_request(self) -> None:
        self.assertIn("HLDspec Minimal Agent UX", self.doc)
        self.assertIn("HLDspec HLD: /path/to/HLD.md create /path/to/target", self.doc)
        self.assertIn("HLDspec create /path/to/target from /path/to/HLD.md", self.doc)
        self.assertIn("/Users/saffi/code/flow/flow-hld.md", self.doc)
        self.assertIn("/Users/saffi/code/flowHld", self.doc)

    def test_minimal_agent_ux_defines_runtime_defaults(self) -> None:
        self.assertIn("Default runtime: claude", self.doc)
        for runtime in ("claude", "codex", "devin"):
            self.assertIn(runtime, self.doc)
        self.assertIn("The first implementation target is Claude", self.doc)
        self.assertIn("Codex and Devin remain supported configuration values", self.doc)

    def test_minimal_agent_ux_keeps_public_facade_and_hides_low_level_scripts(self) -> None:
        self.assertIn("public HLDspec facade", self.doc)
        for command in ("start", "status", "review", "doctor", "continue"):
            self.assertIn(command, self.doc)
        self.assertIn("Do not require the user to know low-level script names", self.doc)

    def test_agents_points_to_minimal_agent_ux_contract(self) -> None:
        trigger = self.agents.split("## HLDspec trigger", 1)[1].split("## Hard rules", 1)[0]
        self.assertIn("docs/HLDSPEC_MINIMAL_AGENT_UX.md", trigger)
        self.assertIn("Default runtime to `claude`", trigger)
        self.assertIn("`claude`, `codex`, and `devin`", trigger)
        self.assertIn("public HLDspec facade", trigger)
        self.assertIn("/Users/saffi/code/flow/flow-hld.md", trigger)
        self.assertIn("/Users/saffi/code/flowHld", trigger)
        self.assertNotIn("hldspec_agent_start.sh", trigger)


if __name__ == "__main__":
    unittest.main()
