"""Tests for specs_missing_test_plans — testing quality gate.

Rules:
- Every spec must have ut_coverage_plan (non-empty)
- Specs without no_direct_user_story: true must also have ui_ux_test_plan
- Technical foundations (no_direct_user_story: true) are exempt from ui_ux_test_plan
"""
from __future__ import annotations

import unittest

from hldspec.prework_contracts import specs_missing_test_plans


def _full_spec(spec_id: str = "spec-001") -> dict:
    return {
        "planned_spec_id": spec_id,
        "title": "Some Feature",
        "ut_coverage_plan": "Test all service methods",
        "ui_ux_test_plan": "Test user journey A -> B",
        "no_direct_user_story": False,
    }


def _technical_spec(spec_id: str = "spec-tech") -> dict:
    return {
        "planned_spec_id": spec_id,
        "title": "Technical Foundation",
        "ut_coverage_plan": "Test all internals",
        "no_direct_user_story": True,
        # ui_ux_test_plan intentionally absent — exempt
    }


class TestFullSpecPasses(unittest.TestCase):

    def test_full_spec_no_missing(self) -> None:
        self.assertEqual([], specs_missing_test_plans([_full_spec()]))

    def test_empty_list_returns_empty(self) -> None:
        self.assertEqual([], specs_missing_test_plans([]))

    def test_multiple_full_specs_pass(self) -> None:
        specs = [_full_spec("s1"), _full_spec("s2"), _full_spec("s3")]
        self.assertEqual([], specs_missing_test_plans(specs))


class TestMissingUtCoveragePlan(unittest.TestCase):

    def test_missing_ut_plan_flagged(self) -> None:
        spec = _full_spec()
        del spec["ut_coverage_plan"]
        result = specs_missing_test_plans([spec])
        self.assertEqual(1, len(result))
        self.assertIn("ut_coverage_plan", result[0]["missing_fields"])

    def test_empty_ut_plan_flagged(self) -> None:
        spec = _full_spec()
        spec["ut_coverage_plan"] = ""
        result = specs_missing_test_plans([spec])
        self.assertEqual(1, len(result))
        self.assertIn("ut_coverage_plan", result[0]["missing_fields"])

    def test_empty_list_ut_plan_flagged(self) -> None:
        spec = _full_spec()
        spec["ut_coverage_plan"] = []
        result = specs_missing_test_plans([spec])
        self.assertEqual(1, len(result))
        self.assertIn("ut_coverage_plan", result[0]["missing_fields"])


class TestMissingUiUxTestPlan(unittest.TestCase):

    def test_missing_ui_ux_plan_flagged_for_user_story_spec(self) -> None:
        spec = _full_spec()
        del spec["ui_ux_test_plan"]
        result = specs_missing_test_plans([spec])
        self.assertEqual(1, len(result))
        self.assertIn("ui_ux_test_plan", result[0]["missing_fields"])

    def test_empty_ui_ux_plan_flagged(self) -> None:
        spec = _full_spec()
        spec["ui_ux_test_plan"] = ""
        result = specs_missing_test_plans([spec])
        self.assertEqual(1, len(result))
        self.assertIn("ui_ux_test_plan", result[0]["missing_fields"])


class TestTechnicalFoundationExemption(unittest.TestCase):

    def test_technical_spec_exempt_from_ui_ux(self) -> None:
        """no_direct_user_story: true exempts from ui_ux_test_plan."""
        result = specs_missing_test_plans([_technical_spec()])
        self.assertEqual([], result)

    def test_technical_spec_still_needs_ut_plan(self) -> None:
        """Technical foundation is NOT exempt from ut_coverage_plan."""
        spec = _technical_spec()
        del spec["ut_coverage_plan"]
        result = specs_missing_test_plans([spec])
        self.assertEqual(1, len(result))
        self.assertIn("ut_coverage_plan", result[0]["missing_fields"])
        self.assertNotIn("ui_ux_test_plan", result[0]["missing_fields"])

    def test_no_direct_user_story_false_still_requires_ui_ux(self) -> None:
        """no_direct_user_story: false is not exempt."""
        spec = _full_spec()
        spec["no_direct_user_story"] = False
        del spec["ui_ux_test_plan"]
        result = specs_missing_test_plans([spec])
        self.assertEqual(1, len(result))
        self.assertIn("ui_ux_test_plan", result[0]["missing_fields"])


class TestResultShape(unittest.TestCase):

    def test_result_includes_spec_id(self) -> None:
        spec = _full_spec("spec-007")
        del spec["ut_coverage_plan"]
        result = specs_missing_test_plans([spec])
        self.assertEqual("spec-007", result[0]["spec_id"])

    def test_result_includes_all_missing_fields(self) -> None:
        """A spec missing both plans shows both in missing_fields."""
        spec = _full_spec()
        del spec["ut_coverage_plan"]
        del spec["ui_ux_test_plan"]
        result = specs_missing_test_plans([spec])
        self.assertIn("ut_coverage_plan", result[0]["missing_fields"])
        self.assertIn("ui_ux_test_plan", result[0]["missing_fields"])

    def test_only_failing_specs_in_result(self) -> None:
        specs = [_full_spec("ok"), _technical_spec("tech")]
        spec_missing_both = {"planned_spec_id": "bad", "title": "Bad"}
        result = specs_missing_test_plans([specs[0], spec_missing_both, specs[1]])
        self.assertEqual(1, len(result))
        self.assertEqual("bad", result[0]["spec_id"])

    def test_non_dict_spec_skipped(self) -> None:
        result = specs_missing_test_plans(["not-a-dict", None])  # type: ignore[list-item]
        self.assertEqual([], result)


if __name__ == "__main__":
    unittest.main()
