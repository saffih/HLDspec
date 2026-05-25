"""Tests for PromotionStatus and DeprecationStatus enums."""
import unittest
from hldspec.promotion import PromotionStatus, DeprecationStatus


class TestPromotionStatus(unittest.TestCase):

    def test_approved_is_terminal(self):
        self.assertIn(PromotionStatus.APPROVED, PromotionStatus.terminal_states())

    def test_superseded_is_terminal(self):
        self.assertIn(PromotionStatus.SUPERSEDED, PromotionStatus.terminal_states())

    def test_rework_required_is_blocking(self):
        self.assertIn(PromotionStatus.REWORK_REQUIRED, PromotionStatus.blocking_states())

    def test_stale_is_blocking(self):
        self.assertIn(PromotionStatus.STALE, PromotionStatus.blocking_states())

    def test_blocked_is_blocking(self):
        self.assertIn(PromotionStatus.BLOCKED, PromotionStatus.blocking_states())

    def test_approval_ready_can_promote(self):
        self.assertTrue(PromotionStatus.APPROVAL_READY.can_promote_to_approved())

    def test_proposed_cannot_promote(self):
        self.assertFalse(PromotionStatus.PROPOSED.can_promote_to_approved())

    def test_rework_required_is_blocking_method(self):
        self.assertTrue(PromotionStatus.REWORK_REQUIRED.is_blocking())

    def test_approved_is_not_blocking(self):
        self.assertFalse(PromotionStatus.APPROVED.is_blocking())

    def test_no_state_is_both_terminal_and_blocking(self):
        overlap = PromotionStatus.terminal_states() & PromotionStatus.blocking_states()
        self.assertEqual(overlap, frozenset())


class TestDeprecationStatus(unittest.TestCase):

    def test_active_is_active_control_signal(self):
        self.assertTrue(DeprecationStatus.ACTIVE.is_active_control_signal())

    def test_deprecated_is_not_active_control_signal(self):
        self.assertFalse(DeprecationStatus.DEPRECATED.is_active_control_signal())

    def test_compatibility_only_is_legacy(self):
        self.assertIn(DeprecationStatus.COMPATIBILITY_ONLY, DeprecationStatus.legacy_states())

    def test_removed_is_legacy(self):
        self.assertIn(DeprecationStatus.REMOVED, DeprecationStatus.legacy_states())

    def test_active_is_not_legacy(self):
        self.assertNotIn(DeprecationStatus.ACTIVE, DeprecationStatus.legacy_states())

    def test_archived_is_legacy(self):
        self.assertIn(DeprecationStatus.ARCHIVED, DeprecationStatus.legacy_states())

    def test_deprecated_is_legacy(self):
        self.assertIn(DeprecationStatus.DEPRECATED, DeprecationStatus.legacy_states())


if __name__ == "__main__":
    unittest.main()
