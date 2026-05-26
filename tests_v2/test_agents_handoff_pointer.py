from __future__ import annotations

import unittest
from pathlib import Path


class AgentsHandoffPointerTests(unittest.TestCase):
    def test_agents_md_points_to_canonical_development_handoff_on_first_screen(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        text = (repo / "AGENTS.md").read_text(encoding="utf-8")
        first_lines = "\n".join(text.splitlines()[:8])

        self.assertIn("HLDspec repo-development handoff:", first_lines)
        self.assertIn("docs/HLDSPEC_DEVELOPMENT_HANDOFF.md", first_lines)
        self.assertIn("docs/HLDSPEC_DEVELOPMENT_BACKLOG.md", first_lines)
        self.assertIn("source of truth", first_lines)

    def test_canonical_handoff_doc_exists(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        self.assertTrue((repo / "docs" / "HLDSPEC_DEVELOPMENT_HANDOFF.md").exists())


if __name__ == "__main__":
    unittest.main()
