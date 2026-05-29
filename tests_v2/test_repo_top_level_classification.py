"""Repo migration Phase 3 — enforced top-level classification.

`docs/REPO_MIGRATION_PLAN.md` carries a "Current top-level classification" table.
This test makes that table a real anti-drift gate (Layer 7): every *tracked*
top-level file or directory must appear, as a backticked token, in that table. If
a new top-level entry is added without classifying it, this test fails — so no
file can be "just there".

Source of truth for "what exists" is `git ls-files` (tracked only), so untracked
scratch (e.g. `.tmp/`, gitignored output) never affects the result.
"""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "docs" / "REPO_MIGRATION_PLAN.md"

CLASSIFICATION_HEADER = "## Current top-level classification"


def tracked_top_level() -> set[str]:
    """Distinct top-level entries (files at depth 1 + first path segment of dirs)."""
    out = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    entries: set[str] = set()
    for line in out.splitlines():
        if not line:
            continue
        entries.add(line.split("/", 1)[0] if "/" in line else line)
    return entries


def classification_section() -> str:
    text = MIGRATION.read_text(encoding="utf-8")
    start = text.index(CLASSIFICATION_HEADER) + len(CLASSIFICATION_HEADER)
    rest = text[start:]
    # End at the next top-level heading.
    nxt = rest.find("\n## ")
    return rest if nxt == -1 else rest[:nxt]


def _classified(entry: str, section: str) -> bool:
    # A directory may be written as `name/`; a file as `name`. Require the
    # backticked token so prose mentions (e.g. the word "docs") do not count.
    return (f"`{entry}`" in section) or (f"`{entry}/`" in section)


class TopLevelClassificationTests(unittest.TestCase):
    def test_classification_section_exists_and_is_nontrivial(self) -> None:
        # Guard against the section being gutted, which would make the
        # per-entry check vacuously pass.
        section = classification_section()
        self.assertTrue(section.strip(), "classification section is empty")
        backticked = section.count("`")
        self.assertGreaterEqual(
            backticked, 40, "classification table has too few backticked tokens"
        )

    def test_tracked_top_level_entries_are_nonempty(self) -> None:
        # Guard against git introspection silently returning nothing.
        self.assertGreaterEqual(len(tracked_top_level()), 15)

    def test_every_tracked_top_level_entry_is_classified(self) -> None:
        section = classification_section()
        missing = sorted(e for e in tracked_top_level() if not _classified(e, section))
        self.assertEqual(
            [],
            missing,
            "REPO_MIGRATION_PLAN.md classification table is missing tracked "
            f"top-level entries: {missing}. Classify each before it can land.",
        )


if __name__ == "__main__":
    unittest.main()
