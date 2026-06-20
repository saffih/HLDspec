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


# Keys that would turn next_slice_packet into an execution channel / NextActionPacket.
# Their absence is what makes "descriptive, not execution" falsifiable.
_EXECUTION_KEYS = frozenset(
    {"command", "argv", "run", "execute", "exec", "ready", "action",
     "action_packet", "next_action", "channel", "invoke"}
)


class BuildArchitecturePackageTests(unittest.TestCase):
    """The emitter (`build_architecture_package`) materializes the typed slot.

    Honest design: only `helper_recommendation` is grounded (injected); the
    human-owned architecture-reasoning fields are emitted empty, so the artifact
    validates ACTION until authored — it never fabricates a PASS.
    """

    def test_emits_all_14_fields_present(self) -> None:
        pkg = j2ap.build_architecture_package(helper_recommendation={"default_helper": "speckit"})
        for field in j2ap.REQUIRED_ARCHITECTURE_PACKAGE_FIELDS:
            self.assertIn(field, pkg)

    def test_emitted_slot_validates_action_until_authored(self) -> None:
        # PO:SI guard — the empty typed slot must NOT pass; it must be honest ACTION.
        pkg = j2ap.build_architecture_package(helper_recommendation={"default_helper": "speckit"})
        result = j2ap.validate_architecture_package(pkg)
        self.assertEqual(result["status"], "ACTION")
        self.assertNotIn("helper_recommendation", result["missing_fields"])  # grounded
        self.assertIn("architecture_intent", result["missing_fields"])       # awaits authorship
        self.assertIn("slice_roadmap", result["missing_fields"])

    def test_embedded_validation_matches_recomputed(self) -> None:
        pkg = j2ap.build_architecture_package(helper_recommendation={"x": 1})
        self.assertEqual(pkg["validation"], j2ap.validate_architecture_package(pkg))
        self.assertEqual(pkg["validation"]["status"], "ACTION")

    def test_complete_authored_package_passes(self) -> None:
        # The validator's contract (Task 4 bullet 1): a complete dict — all 14 fields
        # present and non-empty — is PASS. Authoring the emitted slot reaches PASS.
        pkg = j2ap.build_architecture_package(helper_recommendation={"default_helper": "speckit"})
        authored = dict(pkg)
        authored.update(_valid_package())  # fills all 14 fields with non-empty content
        self.assertEqual(j2ap.validate_architecture_package(authored)["status"], "PASS")

    def test_validation_catches_missing_or_empty_fields(self) -> None:
        # Task 4 bullet 4: empties/removals in the architecture package are caught.
        pkg = j2ap.build_architecture_package(helper_recommendation={"default_helper": "speckit"})
        authored = dict(pkg)
        authored.update(_valid_package())
        self.assertEqual(j2ap.validate_architecture_package(authored)["status"], "PASS")
        authored["contracts_and_seams"] = []  # emptied
        del authored["test_strategy"]          # removed
        result = j2ap.validate_architecture_package(authored)
        self.assertEqual(result["status"], "ACTION")
        self.assertIn("contracts_and_seams", result["missing_fields"])
        self.assertIn("test_strategy", result["missing_fields"])

    def test_next_slice_packet_is_descriptive_not_execution(self) -> None:
        # Task 4 bullet 2: descriptive data, never an execution channel.
        pkg = j2ap.build_architecture_package(helper_recommendation={"default_helper": "speckit"})
        nsp = pkg["next_slice_packet"]
        self.assertIsInstance(nsp, dict)
        self.assertEqual(set(nsp) & _EXECUTION_KEYS, set())
        # A populated descriptive next_slice_packet (slice_id + why) is still pure
        # descriptive data — no execution keys — and the validator accepts it.
        descriptive = {"slice_id": "S1", "why": "establishes the seam first"}
        self.assertEqual(set(descriptive) & _EXECUTION_KEYS, set())
        authored = dict(pkg)
        authored.update(_valid_package())
        authored["next_slice_packet"] = descriptive
        self.assertEqual(j2ap.validate_architecture_package(authored)["status"], "PASS")

    def test_helper_recommendation_grounded_and_advisory(self) -> None:
        # Task 4 bullet 3: advisory. Grounded value lands verbatim; its value never
        # changes the verdict (still ACTION from empty human-owned fields).
        rec = {"default_helper": "speckit", "recommended_helpers": [{"helper_id": "speckit"}]}
        pkg = j2ap.build_architecture_package(helper_recommendation=rec)
        self.assertEqual(pkg["helper_recommendation"], rec)
        for value in ("speckit", "codex", {"default_helper": "devin"}, ["manual"]):
            p = j2ap.build_architecture_package(helper_recommendation=copy.deepcopy(value))
            self.assertEqual(j2ap.validate_architecture_package(p)["status"], "ACTION")

    def test_builder_does_not_import_selection_or_registry(self) -> None:
        # No helper-selection coupling and no registry coupling: the recommendation
        # is injected, not fetched, keeping selection semantics untouched here.
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
        self.assertFalse(any("helper_selection" in n for n in imported), sorted(imported))
        self.assertFalse(any("helper_registry" in n for n in imported), sorted(imported))


if __name__ == "__main__":
    unittest.main()
