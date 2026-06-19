from __future__ import annotations

import copy
import unittest

from hldspec import journey2_architecture_package as j2ap


def _valid_slice(slice_id: str = "S1") -> dict:
    return {
        "id": slice_id,
        "name": "establish config seam",
        "purpose": "introduce the config interface other slices depend on",
        "layer": "infrastructure",
        "allowed_changes": ["add config interface module"],
        "forbidden_changes": ["no product behavior changes"],
        "expected_files_or_areas": ["config/"],
        "required_tests": ["test_config_seam"],
        "dependency_ids": [],
        "risk_level": "low",
        "rollback_story": "revert the single config module commit",
        "architecture_value": "creates the seam behavior slices depend on",
    }


def _valid_package() -> dict:
    return {
        "product_goal_summary": "let users export reports",
        "architecture_intent": "layered service with a stable export seam",
        "source_of_truth_map": {"report_data": "reports service"},
        "ownership_boundaries": {"export": "export module"},
        "contracts_and_seams": ["ExportPort interface"],
        "brownfield_constraints": ["must reuse existing auth middleware"],
        "expert_lenses_applied": {
            "software_architecture": "layering is clean",
            "test_and_evidence": "each slice has tests",
        },
        "domain_assumptions": ["reports fit in memory"],
        "slice_roadmap": [_valid_slice("S1"), _valid_slice("S2")],
        "next_slice_packet": {"slice_id": "S1", "why": "establishes the seam first"},
        "test_strategy": "unit per seam, integration per feature",
        "forbidden_shortcuts": ["no direct DB writes from the UI layer"],
        "growth_and_change_notes": "export formats can grow behind the port",
        "helper_recommendation": {"recommended_helper_id": "speckit"},
    }


class Journey2ArchitecturePackageTests(unittest.TestCase):
    # 1. A valid architecture package passes.
    def test_valid_package_passes(self) -> None:
        result = j2ap.validate_architecture_package(_valid_package())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["missing_fields"], [])
        self.assertEqual(result["slice_findings"], [])

    # 2. Missing a required top-level field fails.
    def test_missing_top_level_field_fails(self) -> None:
        package = _valid_package()
        del package["architecture_intent"]
        result = j2ap.validate_architecture_package(package)
        self.assertEqual(result["status"], "ACTION")
        self.assertIn("architecture_intent", result["missing_fields"])

    # 3. Empty slice roadmap fails.
    def test_empty_slice_roadmap_fails(self) -> None:
        package = _valid_package()
        package["slice_roadmap"] = []
        result = j2ap.validate_architecture_package(package)
        self.assertEqual(result["status"], "ACTION")
        self.assertIn("slice_roadmap", result["missing_fields"])

    # 4. Missing next_slice_packet fails.
    def test_missing_next_slice_packet_fails(self) -> None:
        package = _valid_package()
        del package["next_slice_packet"]
        result = j2ap.validate_architecture_package(package)
        self.assertEqual(result["status"], "ACTION")
        self.assertIn("next_slice_packet", result["missing_fields"])

    # 5. A slice missing tests fails.
    def test_slice_missing_tests_fails(self) -> None:
        package = _valid_package()
        package["slice_roadmap"][0]["required_tests"] = []
        result = j2ap.validate_architecture_package(package)
        self.assertEqual(result["status"], "ACTION")
        self.assertTrue(
            any("required_tests" in f for f in result["slice_findings"]),
            result["slice_findings"],
        )

    # 6. A slice missing a rollback story fails.
    def test_slice_missing_rollback_story_fails(self) -> None:
        package = _valid_package()
        del package["slice_roadmap"][0]["rollback_story"]
        result = j2ap.validate_architecture_package(package)
        self.assertEqual(result["status"], "ACTION")
        self.assertTrue(
            any("rollback_story" in f for f in result["slice_findings"]),
            result["slice_findings"],
        )

    # 7. A mega-slice phrase fails.
    def test_mega_slice_phrase_fails(self) -> None:
        package = _valid_package()
        package["slice_roadmap"][0]["name"] = "implement the whole feature"
        result = j2ap.validate_architecture_package(package)
        self.assertEqual(result["status"], "ACTION")
        self.assertTrue(
            any("too broad" in f for f in result["slice_findings"]),
            result["slice_findings"],
        )

    # 8. A package without expert lenses fails.
    def test_no_expert_lenses_fails(self) -> None:
        package = _valid_package()
        package["expert_lenses_applied"] = {}
        result = j2ap.validate_architecture_package(package)
        self.assertEqual(result["status"], "ACTION")
        self.assertIn("expert_lenses_applied", result["missing_fields"])

    # 9. A package without contracts/seams fails.
    def test_no_contracts_and_seams_fails(self) -> None:
        package = _valid_package()
        package["contracts_and_seams"] = []
        result = j2ap.validate_architecture_package(package)
        self.assertEqual(result["status"], "ACTION")
        self.assertIn("contracts_and_seams", result["missing_fields"])

    # 10. helper_recommendation is a required field, but validation does not touch
    # helper-selection behavior: the module does not import helper_selection, and
    # the recommendation's *value* is irrelevant to the verdict.
    def test_helper_recommendation_is_field_only_no_selection_behavior(self) -> None:
        # The module must not *import* helper selection (a docstring may mention
        # it; an actual import would couple this contract to selection logic).
        import ast
        import inspect

        tree = ast.parse(inspect.getsource(j2ap))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
        self.assertFalse(
            any("helper_selection" in name for name in imported),
            f"module must not import helper_selection; imports: {sorted(imported)}",
        )

        # Required as a presence check: removing it is an ACTION.
        package = _valid_package()
        del package["helper_recommendation"]
        self.assertEqual(
            j2ap.validate_architecture_package(package)["status"], "ACTION"
        )

        # Value-agnostic: any non-empty value passes, regardless of which helper
        # (or even a free-form string) it names -- no selection logic is applied.
        for value in ("speckit", "codex", {"recommended_helper_id": "devin"}, ["manual"]):
            pkg = _valid_package()
            pkg["helper_recommendation"] = copy.deepcopy(value)
            self.assertEqual(
                j2ap.validate_architecture_package(pkg)["status"],
                "PASS",
                f"value {value!r} should not change the verdict",
            )


if __name__ == "__main__":
    unittest.main()
