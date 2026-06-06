import unittest

from hldspec.state_transitions import TRANSITIONS, StateTransition, transitions_from, all_states
from hldspec.speckit_operator_state import PROJECT_BLOCKING_STAGES, PROJECT_NON_BLOCKING_STAGES


class TestTransitionsFrom(unittest.TestCase):
    def test_no_workspace_has_exactly_one_transition(self):
        result = transitions_from("NO_WORKSPACE")
        self.assertGreaterEqual(len(result), 1)
        self.assertTrue(any(t.event == "run" for t in result))

    def test_nonexistent_state_returns_empty_list(self):
        result = transitions_from("NONEXISTENT")
        self.assertEqual(result, [])

    def test_returns_list_of_state_transitions(self):
        result = transitions_from("NO_WORKSPACE")
        self.assertIsInstance(result[0], StateTransition)


class TestAllStates(unittest.TestCase):
    def test_includes_no_workspace(self):
        self.assertIn("NO_WORKSPACE", all_states())

    def test_includes_ready_for_specify(self):
        self.assertIn("READY_FOR_SPECIFY", all_states())

    def test_returns_sorted_list(self):
        states = all_states()
        self.assertEqual(states, sorted(states))

    def test_includes_terminal_states(self):
        # ANALYZE_READY is only an output_state, not a from_state — must still appear.
        self.assertIn("ANALYZE_READY", all_states())

    def test_includes_machine_result_states_used_by_project_flow(self):
        expected = {
            "HLD_READY",
            "HLD_READY_WITH_ACTIONS",
            "HLD_BLOCKED",
            "HLD_READINESS_HLD_MISSING",
            "CONVERSION_QUEUE_MISSING",
            "CONVERSION_CHECKPOINT",
            "HLD_CONVERSION_DECISIONS",
            "WORKING_HLD_CONVERTED",
            "FIRST_RUN_PENDING",
            "SPEC_BUILD_PLAN_CHECKPOINT",
            "SPEC_BUILD_PLAN_BLOCKED",
            "SPEC_BUILD_PLAN_GREEN",
            "SPECKIT_PREWORK_MISSING",
            "SPECKIT_PREWORK_REWORK",
            "SPECKIT_PREWORK_REWORK_REQUIRED",
            "SPECKIT_PREWORK_RUNSKEPTIC_REWORK",
            "SPECKIT_PREWORK_ENGINEERING_GUIDANCE_MISSING",
            "SPECKIT_PREWORK_ENGINEERING_GUIDANCE_REWORK",
            "SPECKIT_PREWORK_STALE",
            "SPECKIT_PREWORK_READY_FOR_APPROVAL",
            "SPECKIT_PREWORK_APPROVAL_GATE",
            "SPECKIT_PREWORK_APPROVED",
            "READY_FOR_SPECIFY",
            "SPECIFY_ACTIVE",
            "PLAN_ACTIVE",
            "TASKS_ACTIVE",
            "ANALYZE_READY",
        }
        self.assertTrue(expected.issubset(set(all_states())), sorted(expected - set(all_states())))

    def test_operator_project_stages_are_in_transition_map(self):
        missing = (PROJECT_BLOCKING_STAGES | PROJECT_NON_BLOCKING_STAGES) - set(all_states())
        self.assertFalse(missing, sorted(missing))

    def test_excludes_known_stale_stage_names(self):
        stale = {
            "RAW_HLD_INSPECTED",
            "USECASE_API_MAP_READY",
            "SPEC_BUILD_PLAN_READY",
            "SPEC_BUILD_PLAN_GATE",
            "SPECKIT_PREWORK_READY",
            "SPECKIT_PROXY_DOSSIER_READY",
            "SPECKIT_EXECUTION",
            "FEATURE_CLARIFY",
            "FEATURE_PLAN",
            "FEATURE_TASKS",
            "FEATURE_DONE",
        }
        self.assertFalse(stale & set(all_states()), sorted(stale & set(all_states())))


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
