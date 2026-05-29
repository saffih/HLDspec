"""Repo layout readability contract.

A new reader must be able to tell active entrypoints, the shared HLD parser, the
V1 sync/downstream pipeline, the session-restart pointer, and the three test
roots apart. This is a pure new-contract test for docs/REPO_LAYOUT.md plus the
DOCS_INDEX pointer to it.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "docs" / "REPO_LAYOUT.md"
DOCS_INDEX = ROOT / "docs" / "DOCS_INDEX.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class RepoLayoutReadabilityTests(unittest.TestCase):
    def test_layout_doc_exists(self) -> None:
        self.assertTrue(LAYOUT.is_file(), f"missing {LAYOUT}")

    def test_layout_doc_names_every_root_file_and_test_root(self) -> None:
        text = _read(LAYOUT)
        for token in (
            "Dev",
            "hld_map.py",
            "hld_spec_sync.py",
            "hld_spec_downstream.py",
            "HLD_FORMAT.md",
            "HLD_GENERATION.md",
            "TERMINOLOGY.md",
            "tests/",
            "tests_v2/",
            "tests_legacy/",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text, f"REPO_LAYOUT.md must classify {token}")

    def test_layout_doc_classifies_roles_not_just_names(self) -> None:
        # Bind to the classification, not the mere filename, so a future edit that
        # drops the meaning fails. Each (token, required-role-phrase) pair must
        # appear on the same line.
        text = _read(LAYOUT)
        lines = text.splitlines()

        def line_with(token: str) -> str:
            matches = [ln for ln in lines if token in ln]
            self.assertTrue(matches, f"no line mentions {token}")
            return " ".join(matches).lower()

        self.assertIn("shared", line_with("hld_map.py"))
        self.assertIn("parser", line_with("hld_map.py"))
        # The V1 pipeline scripts must be marked as V1 and not confused with the
        # V2 hldspec/ module flow.
        self.assertIn("v1", line_with("hld_spec_sync.py"))
        self.assertIn("v1", line_with("hld_spec_downstream.py"))
        # Dev is the session-restart pointer; its purpose must be stated.
        self.assertIn("session", line_with("Dev"))
        # Test roots must be distinguishable.
        self.assertIn("legacy", line_with("tests_legacy/").lower())
        tests_v2_line = line_with("tests_v2/")
        self.assertTrue(
            "primary" in tests_v2_line or "full" in tests_v2_line,
            "tests_v2/ must be marked the primary/full validation suite",
        )

    def test_layout_doc_marks_v1_pipeline_as_still_wired(self) -> None:
        # The V1 scripts are not dead: first_run_readonly.sh still calls them.
        # The doc must say so, or a reader will wrongly delete them.
        text = _read(LAYOUT)
        self.assertIn("first_run_readonly.sh", text)

    def test_docs_index_points_to_repo_layout(self) -> None:
        self.assertIn("REPO_LAYOUT.md", _read(DOCS_INDEX))


if __name__ == "__main__":
    unittest.main()
