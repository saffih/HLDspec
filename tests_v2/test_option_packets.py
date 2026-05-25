from __future__ import annotations

import unittest

from hldspec.option_packet import (
    HUMAN_OWNED_DECISION_TYPES,
    OptionPacket,
    make_option_packet,
)


class TestMakeOptionPacket(unittest.TestCase):
    def _make_minimal(self) -> OptionPacket:
        return make_option_packet(
            "DEC-001",
            missing_fact="Which service owns the user record?",
            options=["auth-service", "user-service"],
            decision_type="source_of_truth",
        )

    def test_make_option_packet_returns_option_packet_type(self):
        result = self._make_minimal()
        self.assertIsInstance(result, OptionPacket)

    def test_required_fields_present(self):
        result = self._make_minimal()
        self.assertEqual(result.decision_id, "DEC-001")
        self.assertEqual(result.missing_fact, "Which service owns the user record?")
        self.assertEqual(result.options, ["auth-service", "user-service"])
        self.assertEqual(result.decision_type, "source_of_truth")

    def test_default_tradeoffs_is_empty_dict(self):
        result = self._make_minimal()
        self.assertEqual(result.tradeoffs, {})

    def test_default_recommended_default_is_empty_string(self):
        result = self._make_minimal()
        self.assertEqual(result.recommended_default, "")

    def test_option_packet_affects_constitution_default_false(self):
        result = self._make_minimal()
        self.assertFalse(result.affects_constitution)


class TestHumanOwnedDecisionTypes(unittest.TestCase):
    def test_human_owned_decision_types_has_six_entries(self):
        self.assertEqual(len(HUMAN_OWNED_DECISION_TYPES), 6)

    def test_source_of_truth_is_human_owned(self):
        self.assertIn("source_of_truth", HUMAN_OWNED_DECISION_TYPES)


if __name__ == "__main__":
    unittest.main()
