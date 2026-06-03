from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEGACY_SURFACE_TERMS = (
    "hldspec_run.sh",
    ".hldspec-first-run",
    "target-spec generation",
)
LEGACY_CONTEXT_TERMS = (
    "legacy",
    "debug",
    "deprecated",
    "historical",
    "status memo",
    "status-vs-design",
    "backlog",
    "older",
    "old layout",
    "compatibility",
    "not the current product",
)


class ProductContractAlignmentTests(unittest.TestCase):
    def test_supported_facade_commands_are_parser_commands(self) -> None:
        help_text = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "hldspec_agent_session.py"), "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        ).stdout
        for command in ("start", "status", "review", "continue", "diff", "doctor", "speckit-doctor"):
            self.assertIn(command, help_text)

    def test_user_run_model_marks_unsupported_commands_future(self) -> None:
        text = (ROOT / "docs" / "USER_RUN_MODEL.md").read_text(encoding="utf-8")
        self.assertIn("Future SpecKit Command", text)
        self.assertIn("Future command.", text)

    def test_agent_first_model_does_not_advertise_future_commands_as_current(self) -> None:
        text = (ROOT / "docs" / "AGENT_FIRST_PRODUCT_MODEL.md").read_text(encoding="utf-8")
        public_section = text.split("Future controls", 1)[0]
        self.assertIn("hldspec continue", public_section)
        self.assertIn("hldspec speckit-doctor", public_section)
        self.assertNotIn("hldspec speckit --target", public_section)
        self.assertNotIn("hldspec stop", public_section)

    def test_target_workspace_doc_uses_canonical_hldspec_sync(self) -> None:
        text = (ROOT / "docs" / "HLD_TO_TARGET_WORKSPACE.md").read_text(encoding="utf-8")
        self.assertIn("target/.hldspec/sync/", text)
        self.assertIn("target/.hldspec/events.jsonl", text)
        self.assertIn("SpecKit-owned workspace files.", text)

    def test_docs_index_does_not_promote_legacy_runner_as_product_surface(self) -> None:
        text = (ROOT / "docs" / "DOCS_INDEX.md").read_text(encoding="utf-8")
        runtime_section = text.split("## Runtime Entry Points", 1)[1].split("## Archive / historical", 1)[0]
        self.assertIn("`scripts/hldspec_agent_session.py` | Current public facade implementation", runtime_section)
        self.assertIn("`scripts/hldspec_run.sh` | Legacy/debug full-pipeline runner", runtime_section)
        self.assertNotIn("Canonical run entry", runtime_section)
        normalized = " ".join(runtime_section.split())
        self.assertIn("must not be presented as the current product workflow", normalized)

    def test_non_archive_docs_contextualize_legacy_command_surface_terms(self) -> None:
        failures: list[str] = []
        for path in (ROOT / "docs").glob("*.md"):
            if path.name in {"HLDSPEC_TERMINOLOGY_AND_FLOW.md"}:
                continue
            lines = path.read_text(encoding="utf-8").splitlines()
            for index, line in enumerate(lines):
                if not any(term in line for term in LEGACY_SURFACE_TERMS):
                    continue
                window = " ".join(lines[max(0, index - 8) : index + 9]).lower()
                if not any(term in window for term in LEGACY_CONTEXT_TERMS):
                    failures.append(f"{path.relative_to(ROOT)}:{index + 1}: {line.strip()}")
        self.assertEqual([], failures)


if __name__ == "__main__":
    unittest.main()
