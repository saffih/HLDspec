import json
import unittest

from hldspec import helper_registry as hr


class RegistryStructureTests(unittest.TestCase):
    def setUp(self):
        self.registry = hr.build_registry()

    def test_registry_includes_speckit(self):
        self.assertIsNotNone(hr.get_helper(self.registry, "speckit"))

    def test_speckit_is_only_implemented_helper(self):
        implemented = [
            h for h in self.registry["helpers"] if h.get("status") == "implemented"
        ]
        self.assertEqual(["speckit"], [h["helper_id"] for h in implemented])

    def test_speckit_lifecycle_is_operational(self):
        speckit = hr.get_helper(self.registry, "speckit")
        self.assertEqual(hr.LIFECYCLE_OPERATIONAL_HELPER, speckit["lifecycle_state"])

    def test_only_operational_helper_is_speckit(self):
        # Proposed/unknown helpers must not be represented as operational.
        operational = hr.operational_helpers(self.registry)
        self.assertEqual(["speckit"], [h["helper_id"] for h in operational])

    def test_authority_excludes_autonomous(self):
        speckit = hr.get_helper(self.registry, "speckit")
        self.assertNotIn(hr.AUTHORITY_AUTONOMOUS_WITH_GUARDS, speckit["authority_levels"])
        self.assertEqual([hr.AUTHORITY_GUIDE_ONLY, hr.AUTHORITY_PROPOSE_COMMAND],
                         speckit["authority_levels"])

    def test_registry_validates_clean(self):
        self.assertEqual([], hr.validate_registry(self.registry))


class NegativeCapabilityTests(unittest.TestCase):
    def setUp(self):
        self.speckit = hr.build_speckit_helper()

    def test_negative_fields_non_empty(self):
        for field_name in hr.NEGATIVE_CAPABILITY_FIELDS:
            self.assertTrue(self.speckit[field_name],
                            msg=f"{field_name} must be non-empty")

    def test_negative_fields_are_concrete(self):
        # Every negative-capability item must pass the concreteness guard.
        for field_name in hr.NEGATIVE_CAPABILITY_FIELDS:
            for item in self.speckit[field_name]:
                self.assertFalse(hr._is_vague(item),
                                 msg=f"{field_name} item not concrete: {item!r}")

    def test_concrete_content_present(self):
        # Authoritative check: the specific concrete capabilities are present,
        # not just non-vague strings.
        forbidden = " ".join(self.speckit["forbidden_actions"]).lower()
        self.assertIn("/speckit.plan", forbidden)
        self.assertIn("/speckit.specify", forbidden)
        self.assertIn("commit, merge, or push", forbidden)

        cannot = " ".join(self.speckit["cannot_do"]).lower()
        self.assertIn("hld_reference_map.json", cannot)
        self.assertIn("constitution.proposed.md", cannot)

        stop = " ".join(self.speckit["stop_rules"]).lower()
        self.assertIn("source_package validation did not pass", stop)

    def test_vague_negative_capability_is_rejected(self):
        bad = hr.build_speckit_helper()
        bad["cannot_do"] = ["do unsafe things", "stop if needed", "some limitations exist"]
        errors = hr.validate_helper(bad)
        self.assertTrue(any("too vague" in e for e in errors), msg=str(errors))

    def test_empty_negative_capability_is_rejected(self):
        bad = hr.build_speckit_helper()
        bad["stop_rules"] = []
        errors = hr.validate_helper(bad)
        self.assertTrue(any("stop_rules" in e for e in errors), msg=str(errors))


class ValidationGuardTests(unittest.TestCase):
    def test_autonomous_authority_is_rejected(self):
        bad = hr.build_speckit_helper()
        bad["authority_levels"] = [hr.AUTHORITY_GUIDE_ONLY, hr.AUTHORITY_AUTONOMOUS_WITH_GUARDS]
        errors = hr.validate_helper(bad)
        self.assertTrue(any("future-only" in e for e in errors), msg=str(errors))

    def test_invalid_lifecycle_is_rejected(self):
        bad = hr.build_speckit_helper()
        bad["lifecycle_state"] = "MADE_UP_STATE"
        errors = hr.validate_helper(bad)
        self.assertTrue(any("invalid lifecycle_state" in e for e in errors), msg=str(errors))

    def test_missing_required_field_is_rejected(self):
        bad = hr.build_speckit_helper()
        del bad["toolchain"]
        errors = hr.validate_helper(bad)
        self.assertTrue(any("toolchain" in e for e in errors), msg=str(errors))

    def test_duplicate_helper_id_is_rejected(self):
        reg = hr.build_registry()
        reg["helpers"].append(hr.build_speckit_helper())
        errors = hr.validate_registry(reg)
        self.assertTrue(any("duplicate helper_id" in e for e in errors), msg=str(errors))


class DeterminismTests(unittest.TestCase):
    def test_registry_json_is_deterministic(self):
        self.assertEqual(hr.registry_json(), hr.registry_json())

    def test_registry_json_is_valid_json_and_round_trips(self):
        text = hr.registry_json()
        loaded = json.loads(text)
        self.assertEqual([], hr.validate_registry(loaded))

    def test_build_registry_is_stable(self):
        self.assertEqual(hr.build_registry(), hr.build_registry())


class SourceOfTruthSeparationTests(unittest.TestCase):
    """JSON canonical; no selection state; no runtime MANIFEST coupling."""

    def test_registry_has_no_selected_helper_state(self):
        reg = hr.build_registry()
        self.assertNotIn("selected_helper", reg)
        self.assertNotIn("helper_selection", reg)
        for helper in reg["helpers"]:
            self.assertNotIn("selected", helper)

    def test_canonical_output_carries_no_manifest_or_selection(self):
        # The canonical artifact (the serialized registry) must not couple a
        # selected helper to runtime MANIFEST provenance or carry selection state.
        text = hr.registry_json()
        self.assertNotIn("MANIFEST", text)
        self.assertNotIn("selected_helper", text)
        self.assertNotIn("helper_selection", text)

    def test_no_markdown_serializer_is_canonical(self):
        # JSON is the only canonical serialization this slice exposes. No public
        # markdown renderer exists yet; if one is added it must be explanatory.
        public_api = [name for name in dir(hr) if not name.startswith("_")]
        self.assertNotIn("registry_md", public_api)
        self.assertFalse(
            [name for name in public_api if name.endswith("_md")],
            msg="no canonical markdown serializer expected in Slice A",
        )
        self.assertEqual("str", type(hr.registry_json()).__name__)


if __name__ == "__main__":
    unittest.main()
