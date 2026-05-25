from __future__ import annotations

import unittest

from hldspec.prework_contracts import (
    augmentation_intact,
    augmented_rule_counts,
    constitution_augmentation_blockers,
)


class TestAugmentedRuleCounts(unittest.TestCase):
    def test_mixed_rules_returns_correct_counts(self):
        constitution = {
            "required_rules": [
                {"rule_id": "CONTRACT-001"},
                {"rule_id": "CONTRACT-002"},
                {"rule_id": "DATA-001"},
                {"rule_id": "UNRELATED-001"},
            ]
        }
        result = augmented_rule_counts(constitution)
        self.assertEqual(result, {"CONTRACT": 2, "DATA": 1})

    def test_no_rules_returns_zeros(self):
        result = augmented_rule_counts({})
        self.assertEqual(result, {"CONTRACT": 0, "DATA": 0})

    def test_empty_required_rules_returns_zeros(self):
        result = augmented_rule_counts({"required_rules": []})
        self.assertEqual(result, {"CONTRACT": 0, "DATA": 0})


class TestAugmentationIntact(unittest.TestCase):
    def test_passes_when_counts_match(self):
        constitution = {
            "required_rules": [
                {"rule_id": "CONTRACT-001"},
                {"rule_id": "DATA-001"},
            ]
        }
        blockers = augmentation_intact(constitution, {"CONTRACT": 1, "DATA": 1})
        self.assertEqual(blockers, [])

    def test_passes_when_counts_exceed_expected(self):
        constitution = {
            "required_rules": [
                {"rule_id": "CONTRACT-001"},
                {"rule_id": "CONTRACT-002"},
                {"rule_id": "DATA-001"},
            ]
        }
        blockers = augmentation_intact(constitution, {"CONTRACT": 1, "DATA": 1})
        self.assertEqual(blockers, [])

    def test_fails_when_contract_count_drops(self):
        constitution = {
            "required_rules": [
                {"rule_id": "DATA-001"},
            ]
        }
        blockers = augmentation_intact(constitution, {"CONTRACT": 2, "DATA": 1})
        self.assertEqual(len(blockers), 1)
        self.assertIn("CONTRACT", blockers[0])
        self.assertIn("expected 2", blockers[0])
        self.assertIn("got 0", blockers[0])

    def test_fails_when_data_count_drops(self):
        constitution = {
            "required_rules": [
                {"rule_id": "CONTRACT-001"},
            ]
        }
        blockers = augmentation_intact(constitution, {"CONTRACT": 1, "DATA": 3})
        self.assertEqual(len(blockers), 1)
        self.assertIn("DATA", blockers[0])
        self.assertIn("expected 3", blockers[0])
        self.assertIn("got 0", blockers[0])


class TestConstitutionAugmentationBlockers(unittest.TestCase):
    def test_blocker_when_augmentation_applied_but_no_augmented_rules(self):
        constitution = {
            "augmentation_applied": True,
            "required_rules": [
                {"rule_id": "UNRELATED-001"},
            ],
        }
        blockers = constitution_augmentation_blockers(constitution)
        self.assertEqual(len(blockers), 1)
        self.assertIn("augmentation_applied=True", blockers[0])

    def test_empty_when_augmentation_applied_absent(self):
        constitution = {
            "required_rules": [
                {"rule_id": "UNRELATED-001"},
            ],
        }
        blockers = constitution_augmentation_blockers(constitution)
        self.assertEqual(blockers, [])

    def test_empty_when_augmentation_applied_and_rules_present(self):
        constitution = {
            "augmentation_applied": True,
            "required_rules": [
                {"rule_id": "CONTRACT-001"},
                {"rule_id": "DATA-001"},
            ],
        }
        blockers = constitution_augmentation_blockers(constitution)
        self.assertEqual(blockers, [])

    def test_empty_when_no_required_rules_and_augmentation_applied(self):
        constitution = {
            "augmentation_applied": True,
            "required_rules": [],
        }
        blockers = constitution_augmentation_blockers(constitution)
        self.assertEqual(len(blockers), 1)

    def test_empty_when_constitution_is_empty(self):
        blockers = constitution_augmentation_blockers({})
        self.assertEqual(blockers, [])


if __name__ == "__main__":
    unittest.main()
