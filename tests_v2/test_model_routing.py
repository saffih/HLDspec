import unittest

from hldspec import model_routing as mr


class CanonicalProjectionTests(unittest.TestCase):
    def test_routine_maps_to_simple(self):
        self.assertEqual(mr.operational_tier(mr.MODEL_ROUTINE), mr.MODEL_SIMPLE)

    def test_default_strong_critical_map_to_smart(self):
        for tier in (mr.MODEL_DEFAULT, mr.MODEL_STRONG, mr.MODEL_CRITICAL):
            self.assertEqual(mr.operational_tier(tier), mr.MODEL_SMART)

    def test_projection_is_lossless_cover(self):
        # Every canonical tier projects to exactly one operational tier.
        for tier in mr.CANONICAL_TIERS:
            self.assertIn(mr.operational_tier(tier), mr.OPERATIONAL_TIERS)

    def test_unknown_canonical_raises(self):
        with self.assertRaises(mr.UnknownOperation):
            mr.operational_tier("MODEL_BOGUS")


class OperationRegistryTests(unittest.TestCase):
    def test_mechanical_is_simple(self):
        for op in ("file_copy", "checksum", "manifest_generation", "mirror_materialization"):
            self.assertEqual(mr.tier_for_operation(op), mr.MODEL_SIMPLE)

    def test_meaning_is_smart(self):
        for op in ("hld_patching", "runskeptic_review", "approval_gate", "continuation_decision"):
            self.assertEqual(mr.tier_for_operation(op), mr.MODEL_SMART)

    def test_requires_smart(self):
        self.assertTrue(mr.requires_smart("constitution_proposal"))
        self.assertFalse(mr.requires_smart("checksum"))

    def test_unknown_operation_raises(self):
        with self.assertRaises(mr.UnknownOperation):
            mr.tier_for_operation("teleport")


class AuthorityGuardTests(unittest.TestCase):
    def test_simple_can_do_simple_only(self):
        self.assertTrue(mr.can_perform(mr.MODEL_SIMPLE, "file_copy"))
        self.assertFalse(mr.can_perform(mr.MODEL_SIMPLE, "hld_patching"))

    def test_smart_can_do_anything(self):
        self.assertTrue(mr.can_perform(mr.MODEL_SMART, "file_copy"))
        self.assertTrue(mr.can_perform(mr.MODEL_SMART, "approval_gate"))

    def test_simple_cannot_own_source_truth(self):
        self.assertFalse(mr.can_own_authority(mr.MODEL_SIMPLE, "approve_source_truth"))
        self.assertFalse(
            mr.can_own_authority(mr.MODEL_SIMPLE, "approve_continuation_after_meaningful_output")
        )
        self.assertFalse(mr.can_own_authority(mr.MODEL_SIMPLE, "resolve_contradiction"))

    def test_smart_can_own_source_truth(self):
        self.assertTrue(mr.can_own_authority(mr.MODEL_SMART, "approve_source_truth"))


if __name__ == "__main__":
    unittest.main()
