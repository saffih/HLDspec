from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CommandSurfaceUseCaseContractTests(unittest.TestCase):
    def test_usecase_doc_has_canonical_command_statuses(self) -> None:
        text = (ROOT / "docs" / "HLDSPEC_USE_CASES_AND_API.md").read_text(encoding="utf-8")
        for command in ("start", "status", "review", "continue", "diff", "doctor", "speckit-doctor", "operator-state", "speckit-state"):
            self.assertIn(f"`hldspec {command}` | current", text)
        for command in ("interview", "prework", "speckit", "pause"):
            self.assertIn(f"`hldspec {command}` | future", text)
        self.assertIn("`hldspec run` | legacy/debug", text)
        self.assertIn("`hldspec speckit-proxy` | legacy/debug", text)
        self.assertIn("direct low-level scripts | legacy/debug", text)

    def test_all_use_cases_have_required_fields(self) -> None:
        text = (ROOT / "docs" / "HLDSPEC_USE_CASES_AND_API.md").read_text(encoding="utf-8")
        for idx in range(1, 24):
            heading = f"### UC-{idx:03d} "
            self.assertIn(heading, text)
            start = text.index(heading)
            next_match = re.search(r"\n### UC-\d{3} ", text[start + 1 :])
            section = text[start : start + 1 + next_match.start()] if next_match else text[start:]
            for field in (
                "- Trigger:",
                "- Preconditions:",
                "- Command/API:",
                "- Artifacts read:",
                "- Artifacts written:",
                "- Stop condition:",
                "- Human decision:",
                "- Tests expected:",
            ):
                self.assertIn(field, section, f"{field} missing from UC-{idx:03d}")

    def test_backlog_records_command_surface_decision(self) -> None:
        text = (ROOT / "docs" / "HLDSPEC_DEVELOPMENT_BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("Overall current mark: 6/10", text)
        self.assertIn("Context economy", text)
        self.assertIn("Seven bounded SpecKit phase prompts are generated", text)
        self.assertIn("Promoted capability RunSkeptic evidence", text)
        self.assertIn("Self-dogfood", text)
        self.assertIn("Decision: keep the current public surface small", text)
        self.assertIn("Current public commands: `start`, `status`, `review`, `continue`, `diff`, `doctor`, `speckit-doctor`.", text)
        self.assertIn("Future commands: `interview`, `prework`, `speckit`, `pause`.", text)
        self.assertIn("Legacy/debug: `run`, `speckit-proxy`, direct low-level scripts.", text)

    def test_user_and_agent_docs_do_not_present_future_commands_as_current(self) -> None:
        agent = (ROOT / "docs" / "AGENT_FIRST_PRODUCT_MODEL.md").read_text(encoding="utf-8")
        current_part = agent.split("Future controls", 1)[0]
        self.assertIn("hldspec continue", current_part)
        self.assertNotIn("hldspec speckit --target", current_part)
        self.assertNotIn("hldspec pause", current_part)

        user = (ROOT / "docs" / "USER_RUN_MODEL.md").read_text(encoding="utf-8")
        self.assertIn("Future product commands:", user)
        self.assertIn("Legacy/debug commands:", user)

    def test_user_run_model_keeps_trigger_phrases_separate_from_command_surface(self) -> None:
        user = (ROOT / "docs" / "USER_RUN_MODEL.md").read_text(encoding="utf-8")
        self.assertIn("Trigger phrases such as `check HLD`, `Build Loop prereqs`, `Build Loop init`, `Build Loop ready`, and `HLDspec help ...` are user-facing workflow requests.", user)
        self.assertIn("They are not currently separate CLI commands in the product facade.", user)


if __name__ == "__main__":
    unittest.main()
