"""Anti-drift guard for the invariant-to-test binding principle.

The idea: every invariant stated in an HLD (HLD-VERIFY on HIGH-risk anchors) must
be bound to a failing-if-violated test — a documented principle is not enough, it
needs an enforcing mechanism. This was learned the hard way (a working runtime had
three live bugs because its invariants were stated but not enforced).

This test makes the principle itself un-loseable: if anyone deletes the gate
script, drops it from the principle matrix, unwires it from the slice policy, or
removes its tests, one of these assertions goes red. It is the lesson applied to
the lesson.
"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


class InvariantCoveragePrincipleTests(unittest.TestCase):
    def test_gate_script_exists(self) -> None:
        self.assertTrue(
            (REPO / "scripts" / "hld_verify_coverage.py").is_file(),
            "the HLD-VERIFY coverage gate script must exist",
        )

    def test_matrix_documents_the_idea_and_names_the_gate(self) -> None:
        matrix = (REPO / "docs" / "HLDSPEC_PRINCIPLE_ENFORCEMENT_MATRIX.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("HLD-VERIFY", matrix)
        self.assertIn("hld_verify_coverage", matrix)

    def test_slice_policy_wires_the_gate(self) -> None:
        slicing = (REPO / "hldspec" / "implementation_slicing.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("hld_verify_coverage", slicing)
        self.assertIn("HLD-VERIFY", slicing)

    def test_gate_has_its_own_unit_tests(self) -> None:
        self.assertTrue(
            (REPO / "tests_v2" / "test_hld_verify_coverage.py").is_file(),
            "the gate must itself be under test",
        )


if __name__ == "__main__":
    unittest.main()
