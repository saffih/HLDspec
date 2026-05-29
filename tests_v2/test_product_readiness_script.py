"""Structural contract for scripts/check_product_readiness.sh.

This test is intentionally structural: it does NOT execute the script (the
script runs the full tests_v2 suite + smoke, and this module is part of that
suite, so executing it here would recurse). It verifies the script exists, is a
bash script, and actually invokes the real check targets by name. The strong
evidence that the script works is running it once directly; see
docs/PRODUCT_READINESS.md.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_product_readiness.sh"
README = ROOT / "README.md"


class ProductReadinessScriptTests(unittest.TestCase):
    def test_script_exists(self) -> None:
        self.assertTrue(SCRIPT.is_file(), f"missing {SCRIPT}")

    def test_script_is_bash(self) -> None:
        first_line = SCRIPT.read_text(encoding="utf-8").splitlines()[0]
        self.assertTrue(first_line.startswith("#!") and "sh" in first_line, first_line)

    def test_script_invokes_real_check_targets(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        for target in (
            "tests_v2.test_speckit_operator_state",
            "tests_v2.test_speckit_readiness",
            "tests_v2.test_anti_drift_contracts",
            "tests_v2.test_terminology_and_flow_docs",
            "tests_v2.test_product_readiness_docs",
            "tests_v2.test_repo_layout_readability",
            "discover -s tests_v2",
            "hldspec_smoke_slice_e2e.py",
            "git diff --check",
        ):
            with self.subTest(target=target):
                self.assertIn(target, text, f"check script must run {target}")

    def test_readme_references_the_script(self) -> None:
        self.assertIn("check_product_readiness.sh", README.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
