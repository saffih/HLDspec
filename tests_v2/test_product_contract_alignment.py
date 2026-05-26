from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ProductContractAlignmentTests(unittest.TestCase):
    def test_supported_facade_commands_are_parser_commands(self) -> None:
        help_text = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "hldspec_agent_session.py"), "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        ).stdout
        for command in ("start", "status", "review", "continue", "diff", "doctor"):
            self.assertIn(command, help_text)

    def test_user_run_model_marks_unsupported_commands_future(self) -> None:
        text = (ROOT / "docs" / "USER_RUN_MODEL.md").read_text(encoding="utf-8")
        self.assertIn("Future SpecKit Command", text)
        self.assertIn("Future command.", text)

    def test_agent_first_model_does_not_advertise_future_commands_as_current(self) -> None:
        text = (ROOT / "docs" / "AGENT_FIRST_PRODUCT_MODEL.md").read_text(encoding="utf-8")
        public_section = text.split("Future controls", 1)[0]
        self.assertIn("hldspec continue", public_section)
        self.assertNotIn("hldspec speckit", public_section)
        self.assertNotIn("hldspec stop", public_section)

    def test_target_workspace_doc_uses_canonical_hldspec_sync(self) -> None:
        text = (ROOT / "docs" / "HLD_TO_TARGET_WORKSPACE.md").read_text(encoding="utf-8")
        self.assertIn("target/.hldspec/sync/", text)
        self.assertIn("target/.hldspec/events.jsonl", text)
        self.assertIn("SpecKit-owned workspace files.", text)


if __name__ == "__main__":
    unittest.main()
