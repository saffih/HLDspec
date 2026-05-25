"""P2-22 — Renderer contract tests.

Asserts that render_machine_result always includes required sections
for each MachineStatus variant.
"""
from __future__ import annotations

import unittest

from hldspec.result_renderer import render_machine_result
from hldspec.state_machine import (
    ArtifactRef,
    CheckpointKind,
    HumanQuestion,
    blocked_result,
    continue_result,
    done_result,
    error_result,
    human_checkpoint,
)


class StopCheckpointRendererTests(unittest.TestCase):
    def _make_result(self, **kwargs):
        defaults = dict(
            machine="TestMachine",
            state="TEST_STATE",
            kind=CheckpointKind.HLD_CONVERSION_DECISIONS,
            blocking_reason="Decisions are still TBD.",
            questions=(
                HumanQuestion(
                    question_id="Q-001",
                    title="Keep or split?",
                    question="Keep or split?",
                    options=("KEEP_AS_ONE", "SPLIT"),
                ),
            ),
            controlling_artifacts=(),
            next_action="Update the queue and rerun.",
            forbidden_actions=("Do not modify source HLD.",),
        )
        defaults.update(kwargs)
        return human_checkpoint(**defaults)

    def test_contains_checkpoint_label(self):
        text = render_machine_result(self._make_result())
        self.assertIn("CHECKPOINT", text)

    def test_contains_blocking_reason(self):
        result = self._make_result(blocking_reason="Something is blocking.")
        text = render_machine_result(result)
        self.assertIn("Something is blocking.", text)

    def test_contains_at_least_one_option(self):
        result = self._make_result(
            questions=(
                HumanQuestion(
                    question_id="Q-001",
                    title="Keep or split?",
                    question="Keep or split?",
                    options=("KEEP_AS_ONE", "SPLIT"),
                ),
            )
        )
        text = render_machine_result(result)
        self.assertIn("KEEP_AS_ONE", text)

    def test_contains_next_action(self):
        result = self._make_result(next_action="Update the queue and rerun.")
        text = render_machine_result(result)
        # next_action appears under "Continuation protocol:"
        self.assertIn("Update the queue and rerun.", text)

    def test_contains_forbidden_section_when_forbidden_actions_exist(self):
        result = self._make_result(
            forbidden_actions=("Do not invoke SpecKit.", "Do not implement app code.")
        )
        text = render_machine_result(result)
        self.assertIn("What is not modified / not invoked:", text)
        self.assertIn("Do not invoke SpecKit.", text)

    def test_contains_artifact_paths_when_controlling_artifacts_provided(self):
        result = self._make_result(
            controlling_artifacts=(
                ArtifactRef(path="/path/to/queue.json", role="decision_queue"),
            )
        )
        text = render_machine_result(result)
        self.assertIn("/path/to/queue.json", text)


class BlockedRendererTests(unittest.TestCase):
    def _make_result(self, blocking_reason="Artifact is missing."):
        return blocked_result(
            machine="TestMachine",
            state="SPECKIT_PREWORK_MISSING",
            kind=CheckpointKind.SPECKIT_PREWORK_MISSING,
            blocking_reason=blocking_reason,
        )

    def test_contains_blocked_status(self):
        text = render_machine_result(self._make_result())
        self.assertIn("BLOCKED", text)

    def test_contains_blocking_reason(self):
        result = self._make_result(blocking_reason="Specific artifact is missing.")
        text = render_machine_result(result)
        self.assertIn("Specific artifact is missing.", text)


class ContinueRendererTests(unittest.TestCase):
    def test_contains_machine_name(self):
        result = continue_result(machine="SpecBuildPlanMachine", state="SPEC_BUILD_PLAN_PASSED")
        text = render_machine_result(result)
        self.assertIn("SpecBuildPlanMachine", text)

    def test_contains_state(self):
        result = continue_result(machine="SpecBuildPlanMachine", state="SPEC_BUILD_PLAN_PASSED")
        text = render_machine_result(result)
        self.assertIn("SPEC_BUILD_PLAN_PASSED", text)


class DoneRendererTests(unittest.TestCase):
    def test_contains_machine_name(self):
        result = done_result(machine="ApprovalGateMachine", state="APPROVED")
        text = render_machine_result(result)
        self.assertIn("ApprovalGateMachine", text)


class ErrorRendererTests(unittest.TestCase):
    def test_contains_error_label(self):
        result = error_result(machine="TestMachine", state="CRASHED", message="Something went wrong.")
        text = render_machine_result(result)
        self.assertIn("ERROR", text)

    def test_contains_error_message(self):
        result = error_result(machine="TestMachine", state="CRASHED", message="Something went wrong.")
        text = render_machine_result(result)
        self.assertIn("Something went wrong.", text)


if __name__ == "__main__":
    unittest.main()
