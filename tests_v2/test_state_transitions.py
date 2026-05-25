import unittest

from hldspec.state_transitions import TRANSITIONS, StateTransition, transitions_from, all_states


class TestTransitionsFrom(unittest.TestCase):
    def test_no_workspace_has_exactly_one_transition(self):
        result = transitions_from("NO_WORKSPACE")
        self.assertEqual(len(result), 1)

    def test_nonexistent_state_returns_empty_list(self):
        result = transitions_from("NONEXISTENT")
        self.assertEqual(result, [])

    def test_returns_list_of_state_transitions(self):
        result = transitions_from("NO_WORKSPACE")
        self.assertIsInstance(result[0], StateTransition)


class TestAllStates(unittest.TestCase):
    def test_includes_no_workspace(self):
        self.assertIn("NO_WORKSPACE", all_states())

    def test_includes_speckit_execution(self):
        self.assertIn("SPECKIT_EXECUTION", all_states())

    def test_returns_sorted_list(self):
        states = all_states()
        self.assertEqual(states, sorted(states))

    def test_includes_terminal_states(self):
        # FEATURE_DONE is only an output_state, not a from_state — must still appear
        self.assertIn("FEATURE_DONE", all_states())


class TestTransitionIntegrity(unittest.TestCase):
    def test_all_transitions_have_non_empty_from_state(self):
        for t in TRANSITIONS:
            self.assertTrue(t.from_state, f"Empty from_state in {t}")

    def test_all_transitions_have_non_empty_event(self):
        for t in TRANSITIONS:
            self.assertTrue(t.event, f"Empty event in {t}")

    def test_all_transitions_have_non_empty_guard(self):
        for t in TRANSITIONS:
            self.assertTrue(t.guard, f"Empty guard in {t}")

    def test_all_transitions_have_non_empty_action(self):
        for t in TRANSITIONS:
            self.assertTrue(t.action, f"Empty action in {t}")

    def test_all_transitions_have_non_empty_output_state(self):
        for t in TRANSITIONS:
            self.assertTrue(t.output_state, f"Empty output_state in {t}")

    def test_no_duplicate_from_state_event_combinations(self):
        seen = set()
        for t in TRANSITIONS:
            key = (t.from_state, t.event)
            self.assertNotIn(key, seen, f"Duplicate (from_state, event): {key}")
            seen.add(key)

    def test_every_transition_has_artifact_or_notes(self):
        for t in TRANSITIONS:
            self.assertTrue(
                t.required_artifacts or t.notes,
                f"Transition {t.from_state}->{t.event} has no required_artifacts and no notes",
            )


if __name__ == "__main__":
    unittest.main()
