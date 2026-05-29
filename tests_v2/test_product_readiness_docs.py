"""Product-readiness documentation contract.

Two kinds of checks:

* Real-artifact: the README command surface is validated against the actual
  argparse parser in hldspec_agent_session.build_parser(), so adding a public
  command without documenting it fails (drift in both directions).
* New-contract: docs/PRODUCT_READINESS.md must exist, name the three tiers, and
  not overclaim production readiness.
"""
from __future__ import annotations

import argparse
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
SCORECARD = ROOT / "docs" / "PRODUCT_READINESS.md"

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
import hldspec_agent_session  # noqa: E402


def public_commands() -> set[str]:
    parser = hldspec_agent_session.build_parser()
    names: set[str] = set()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            names.update(action.choices.keys())
    return names


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class ProductReadinessDocsTests(unittest.TestCase):
    def test_parser_surface_is_nontrivial(self) -> None:
        # Guard against the introspection silently returning nothing, which would
        # make the command-surface assertion vacuously pass.
        commands = public_commands()
        self.assertIn("operator-state", commands)
        self.assertIn("speckit-state", commands)
        self.assertGreaterEqual(len(commands), 9)

    def test_readme_documents_every_public_command(self) -> None:
        # Require each command as a backtick-quoted token (table cell / inline
        # code), not a bare substring. Prose like "git diff" / "git status" must
        # not satisfy the check, so deleting a command's documented row fails.
        readme = _read(README)
        for command in sorted(public_commands()):
            with self.subTest(command=command):
                self.assertIn(
                    f"`{command}`",
                    readme,
                    f"README must document the '{command}' command as a `{command}` token",
                )

    def test_readme_explains_decision_vocabulary(self) -> None:
        readme = _read(README)
        for token in ("PASS", "ACTION", "CONFLICT"):
            with self.subTest(token=token):
                self.assertIn(token, readme)

    def test_readme_links_scorecard_and_states_greenfield_scope(self) -> None:
        readme = _read(README)
        self.assertIn("PRODUCT_READINESS.md", readme)
        self.assertIn("greenfield", readme.lower())

    def test_scorecard_exists(self) -> None:
        self.assertTrue(SCORECARD.is_file(), f"missing {SCORECARD}")

    def test_scorecard_names_three_tiers(self) -> None:
        text = _read(SCORECARD)
        for tier in ("Supervised MVP", "Standalone user", "Production"):
            with self.subTest(tier=tier):
                self.assertIn(tier, text)

    def test_scorecard_does_not_overclaim_production(self) -> None:
        text = _read(SCORECARD)
        self.assertIn("Production-ready: NO", text)

    def test_scorecard_names_runskeptic_verification(self) -> None:
        self.assertIn("RunSkeptic", _read(SCORECARD))

    def test_scorecard_uses_nonbrittle_test_evidence(self) -> None:
        # The full-suite evidence must be a re-runnable command, not a hardcoded
        # pass count that goes stale as tests are added. Guards against
        # reintroducing wording like "discover -s tests_v2 -> 673 OK".
        text = _read(SCORECARD)
        self.assertIn("discover -s tests_v2", text)
        stale = re.search(r"\b\d+\s+OK\b", text)
        self.assertIsNone(
            stale,
            f"scorecard has a brittle hardcoded test count: {stale.group(0) if stale else ''}",
        )


if __name__ == "__main__":
    unittest.main()
