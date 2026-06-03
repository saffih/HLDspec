"""P2-23 — CLI UX contract tests.

Asserts that render_machine_result always includes the 7 required fields from
the CLI UX contract, and that the CLI exits with code 2 on STOP_CHECKPOINT.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from hldspec.result_renderer import render_machine_result
from hldspec.state_machine import (
    ArtifactRef,
    CheckpointKind,
    HumanQuestion,
    RunSkepticStatus,
    blocked_result,
    continue_result,
    done_result,
    error_result,
    human_checkpoint,
)


def _make_stop_checkpoint(
    *,
    machine="TestMachine",
    state="TEST_GATE",
    forbidden_actions=("Do not invoke SpecKit.",),
    controlling_artifacts=(),
    next_action="Update queue and rerun.",
) -> object:
    return human_checkpoint(
        machine=machine,
        state=state,
        kind=CheckpointKind.HLD_CONVERSION_DECISIONS,
        blocking_reason="Decisions are TBD.",
        questions=(
            HumanQuestion(
                question_id="Q-001",
                title="Keep or split?",
                question="Keep or split?",
                options=("KEEP_AS_ONE", "SPLIT"),
            ),
        ),
        controlling_artifacts=controlling_artifacts,
        next_action=next_action,
        forbidden_actions=forbidden_actions,
    )


class UxContractStopCheckpointTests(unittest.TestCase):
    """Verify STOP_CHECKPOINT renders all 7 required UX fields."""

    def setUp(self):
        self.result = _make_stop_checkpoint()
        self.text = render_machine_result(self.result)

    def test_machine_name_is_shown(self):
        self.assertIn("TestMachine", self.text)

    def test_current_state_is_shown(self):
        # state is rendered as "State: <value>"
        self.assertIn("TEST_GATE", self.text)

    def test_checkpoint_kind_is_shown(self):
        self.assertIn("HLD_CONVERSION_DECISIONS", self.text)

    def test_decision_options_are_shown(self):
        self.assertIn("KEEP_AS_ONE", self.text)
        self.assertIn("SPLIT", self.text)

    def test_forbidden_actions_are_shown(self):
        self.assertIn("Do not invoke SpecKit.", self.text)

    def test_next_action_is_shown(self):
        self.assertIn("Update queue and rerun.", self.text)

    def test_artifact_paths_are_shown_when_present(self):
        result = _make_stop_checkpoint(
            controlling_artifacts=(ArtifactRef(path="/workspace/queue.json", role="decision_queue"),)
        )
        text = render_machine_result(result)
        self.assertIn("/workspace/queue.json", text)

    def test_runskeptic_status_and_evidence_are_shown(self):
        result = human_checkpoint(
            machine="TestMachine",
            state="RUNSKEPTIC_GATE",
            kind=CheckpointKind.SPECKIT_PREWORK_REWORK,
            blocking_reason="RunSkeptic found rework.",
            questions=(),
            controlling_artifacts=(),
            next_action="Fix RunSkeptic findings.",
            forbidden_actions=("Do not invoke SpecKit.",),
            runskeptic=RunSkepticStatus(
                status="ACTION",
                evidence=(ArtifactRef(path="/workspace/runskeptic.json", role="runskeptic_review_json"),),
                next_safe_action="Resolve findings before continuing.",
            ),
        )

        text = render_machine_result(result)

        self.assertIn("RunSkeptic:", text)
        self.assertIn("Status: ACTION", text)
        self.assertIn("/workspace/runskeptic.json", text)
        self.assertIn("Resolve findings before continuing.", text)


class UxContractOtherStatusTests(unittest.TestCase):
    def test_continue_shows_machine_name_and_state(self):
        result = continue_result(machine="SpecBuildPlanMachine", state="PLAN_PASSED")
        text = render_machine_result(result)
        self.assertIn("SpecBuildPlanMachine", text)
        self.assertIn("PLAN_PASSED", text)

    def test_done_shows_machine_name(self):
        result = done_result(machine="ApprovalGateMachine", state="APPROVED")
        text = render_machine_result(result)
        self.assertIn("ApprovalGateMachine", text)

    def test_blocked_shows_machine_name_and_state(self):
        result = blocked_result(
            machine="SpeckitPreworkMachine",
            state="SPECKIT_PREWORK_MISSING",
            kind=CheckpointKind.SPECKIT_PREWORK_MISSING,
            blocking_reason="Prework missing.",
        )
        text = render_machine_result(result)
        self.assertIn("SpeckitPreworkMachine", text)
        self.assertIn("SPECKIT_PREWORK_MISSING", text)

    def test_error_shows_machine_name(self):
        result = error_result(machine="TestMachine", state="CRASHED", message="Error msg.")
        text = render_machine_result(result)
        self.assertIn("TestMachine", text)


class CliExitCodeTests(unittest.TestCase):
    """Verify the CLI exit-code contract for each MachineStatus value.

    hldspec_v2.py maps MachineResult.exit_code() to the process exit code.
    These tests verify that contract at the unit level:
      STOP_CHECKPOINT -> 2
      BLOCKED         -> 3
      DONE/CONTINUE   -> 0
      ERROR           -> 1
    """

    def test_stop_checkpoint_exit_code_is_2(self):
        """STOP_CHECKPOINT result must produce exit code 2."""
        from hldspec.state_machine import ExitCode
        result = _make_stop_checkpoint()
        self.assertEqual(ExitCode.HUMAN_CHECKPOINT_REQUIRED, result.exit_code())
        self.assertEqual(2, result.exit_code().value)

    def test_blocked_exit_code_is_3(self):
        result = blocked_result(
            machine="M",
            state="S",
            kind=CheckpointKind.SPECKIT_PREWORK_MISSING,
            blocking_reason="reason",
        )
        self.assertEqual(3, result.exit_code().value)

    def test_done_exit_code_is_0(self):
        result = done_result(machine="M", state="S")
        self.assertEqual(0, result.exit_code().value)

    def test_error_exit_code_is_1(self):
        result = error_result(machine="M", state="S", message="boom")
        self.assertEqual(1, result.exit_code().value)

    def test_continue_exit_code_is_0(self):
        result = continue_result(machine="M", state="S")
        self.assertEqual(0, result.exit_code().value)


if __name__ == "__main__":
    unittest.main()
