"""Tests for SpecKitExecutionMachine.

Covers:
- Missing inputs (no workspace, no queue, invalid queue)
- Constitution phase: pending, decision-in-state → continue, already approved
- Feature phases: CLARIFY/PLAN/TASKS pending, COMPLETE → advance phase, DONE → advance feature
- Completion: all features done
- State is written correctly across transitions
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec.machines.speckit_execution import (
    PHASE_CLARIFY,
    PHASE_DONE,
    PHASE_PLAN,
    PHASE_TASKS,
    SpecKitExecutionMachine,
)
from hldspec.state_machine import MachineContext, MachineStatus


def _sync(workspace: Path) -> Path:
    return workspace / "firstrun" / ".specify" / "sync"


def _write_queue(sync: Path, features: list) -> None:
    sync.mkdir(parents=True, exist_ok=True)
    (sync / "speckit_invocation_queue.json").write_text(
        json.dumps({"items": features}), encoding="utf-8"
    )


def _write_state(sync: Path, state: dict) -> None:
    sync.mkdir(parents=True, exist_ok=True)
    (sync / "speckit_execution_state.json").write_text(
        json.dumps(state), encoding="utf-8"
    )


def _read_state(sync: Path) -> dict:
    path = sync / "speckit_execution_state.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _ctx(workspace: Path) -> MachineContext:
    return MachineContext(repo_root=str(workspace), workspace=str(workspace))


def _feature(feature_id: str = "feat-001", name: str = "Feature One") -> dict:
    return {
        "feature_id": feature_id,
        "feature_name": name,
        "speckit_specify_input": feature_id,
        "depends_on_features": [],
        "source_hld_sections": [],
    }


class TestMissingInputs(unittest.TestCase):

    def test_no_workspace_returns_error(self) -> None:
        result = SpecKitExecutionMachine().run(
            MachineContext(repo_root="/tmp", workspace=None)
        )
        self.assertEqual(MachineStatus.ERROR, result.status)
        self.assertEqual("NO_WORKSPACE", result.state)

    def test_queue_missing_returns_blocked(self) -> None:
        ws = Path(tempfile.mkdtemp())
        result = SpecKitExecutionMachine().run(_ctx(ws))
        self.assertEqual(MachineStatus.BLOCKED, result.status)
        self.assertEqual("QUEUE_MISSING", result.state)

    def test_queue_invalid_items_not_a_list_returns_error(self) -> None:
        ws = Path(tempfile.mkdtemp())
        sync = _sync(ws)
        sync.mkdir(parents=True, exist_ok=True)
        (sync / "speckit_invocation_queue.json").write_text(
            json.dumps({"items": "not-a-list"}), encoding="utf-8"
        )
        result = SpecKitExecutionMachine().run(_ctx(ws))
        self.assertEqual(MachineStatus.ERROR, result.status)
        self.assertEqual("QUEUE_INVALID", result.state)


class TestConstitutionPhase(unittest.TestCase):

    def test_no_state_produces_constitution_pending_checkpoint(self) -> None:
        ws = Path(tempfile.mkdtemp())
        _write_queue(_sync(ws), [_feature()])
        result = SpecKitExecutionMachine().run(_ctx(ws))
        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        self.assertEqual("CONSTITUTION_PENDING", result.state)
        assert result.checkpoint is not None
        self.assertTrue(result.checkpoint.has_open_questions())

    def test_constitution_decision_approved_in_state_produces_continue(self) -> None:
        ws = Path(tempfile.mkdtemp())
        _write_queue(_sync(ws), [_feature()])
        _write_state(_sync(ws), {"constitution_decision": "APPROVED"})

        result = SpecKitExecutionMachine().run(_ctx(ws))

        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("CONSTITUTION_APPROVED", result.state)
        # State should now record constitution_approved=True
        self.assertTrue(_read_state(_sync(ws)).get("constitution_approved"))

    def test_constitution_needs_review_still_blocks(self) -> None:
        ws = Path(tempfile.mkdtemp())
        _write_queue(_sync(ws), [_feature()])
        _write_state(_sync(ws), {"constitution_decision": "NEEDS_REVIEW"})
        result = SpecKitExecutionMachine().run(_ctx(ws))
        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        self.assertEqual("CONSTITUTION_PENDING", result.state)


class TestAllFeaturesComplete(unittest.TestCase):

    def test_empty_queue_after_constitution_approval_is_all_complete(self) -> None:
        ws = Path(tempfile.mkdtemp())
        _write_queue(_sync(ws), [])
        _write_state(_sync(ws), {"constitution_approved": True})
        result = SpecKitExecutionMachine().run(_ctx(ws))
        self.assertEqual(MachineStatus.DONE, result.status)
        self.assertEqual("ALL_FEATURES_COMPLETE", result.state)

    def test_index_past_last_feature_is_all_complete(self) -> None:
        ws = Path(tempfile.mkdtemp())
        _write_queue(_sync(ws), [_feature()])
        _write_state(_sync(ws), {"constitution_approved": True, "active_feature_index": 1})
        result = SpecKitExecutionMachine().run(_ctx(ws))
        self.assertEqual(MachineStatus.DONE, result.status)
        self.assertEqual("ALL_FEATURES_COMPLETE", result.state)
        self.assertTrue(_read_state(_sync(ws)).get("all_complete"))


class TestFeaturePhases(unittest.TestCase):

    def _approved_state(self, **extra) -> dict:
        return {"constitution_approved": True, "active_feature_index": 0, **extra}

    def test_clarify_pending_produces_checkpoint(self) -> None:
        ws = Path(tempfile.mkdtemp())
        _write_queue(_sync(ws), [_feature()])
        _write_state(_sync(ws), self._approved_state(active_phase=PHASE_CLARIFY))
        result = SpecKitExecutionMachine().run(_ctx(ws))
        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        self.assertEqual("CLARIFY_PENDING", result.state)
        assert result.checkpoint is not None
        self.assertTrue(result.checkpoint.has_open_questions())

    def test_clarify_default_phase_is_used_when_not_set(self) -> None:
        """active_phase defaults to CLARIFY when missing from state."""
        ws = Path(tempfile.mkdtemp())
        _write_queue(_sync(ws), [_feature()])
        _write_state(_sync(ws), {"constitution_approved": True, "active_feature_index": 0})
        result = SpecKitExecutionMachine().run(_ctx(ws))
        self.assertEqual("CLARIFY_PENDING", result.state)

    def test_clarify_complete_advances_to_plan(self) -> None:
        ws = Path(tempfile.mkdtemp())
        feat = _feature("feat-001")
        _write_queue(_sync(ws), [feat])
        _write_state(_sync(ws), {**self._approved_state(active_phase=PHASE_CLARIFY), **{"feat-001_CLARIFY_decision": "COMPLETE"}})
        result = SpecKitExecutionMachine().run(_ctx(ws))
        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("CLARIFY_COMPLETE", result.state)
        self.assertEqual(PHASE_PLAN, _read_state(_sync(ws)).get("active_phase"))

    def test_plan_pending_produces_checkpoint(self) -> None:
        ws = Path(tempfile.mkdtemp())
        _write_queue(_sync(ws), [_feature()])
        _write_state(_sync(ws), self._approved_state(active_phase=PHASE_PLAN))
        result = SpecKitExecutionMachine().run(_ctx(ws))
        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        self.assertEqual("PLAN_PENDING", result.state)

    def test_plan_complete_advances_to_tasks(self) -> None:
        ws = Path(tempfile.mkdtemp())
        feat = _feature("feat-001")
        _write_queue(_sync(ws), [feat])
        _write_state(_sync(ws), {**self._approved_state(active_phase=PHASE_PLAN), **{"feat-001_PLAN_decision": "COMPLETE"}})
        result = SpecKitExecutionMachine().run(_ctx(ws))
        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("PLAN_COMPLETE", result.state)
        self.assertEqual(PHASE_TASKS, _read_state(_sync(ws)).get("active_phase"))

    def test_tasks_pending_produces_checkpoint(self) -> None:
        ws = Path(tempfile.mkdtemp())
        _write_queue(_sync(ws), [_feature()])
        _write_state(_sync(ws), self._approved_state(active_phase=PHASE_TASKS))
        result = SpecKitExecutionMachine().run(_ctx(ws))
        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        self.assertEqual("TASKS_PENDING", result.state)

    def test_tasks_complete_advances_to_done(self) -> None:
        ws = Path(tempfile.mkdtemp())
        feat = _feature("feat-001")
        _write_queue(_sync(ws), [feat])
        _write_state(_sync(ws), {**self._approved_state(active_phase=PHASE_TASKS), **{"feat-001_TASKS_decision": "COMPLETE"}})
        result = SpecKitExecutionMachine().run(_ctx(ws))
        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("TASKS_COMPLETE", result.state)
        self.assertEqual(PHASE_DONE, _read_state(_sync(ws)).get("active_phase"))

    def test_phase_done_advances_feature_index(self) -> None:
        ws = Path(tempfile.mkdtemp())
        _write_queue(_sync(ws), [_feature("feat-001"), _feature("feat-002", "Feature Two")])
        _write_state(_sync(ws), self._approved_state(active_phase=PHASE_DONE))
        result = SpecKitExecutionMachine().run(_ctx(ws))
        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("FEATURE_ADVANCED", result.state)
        state = _read_state(_sync(ws))
        self.assertEqual(1, state.get("active_feature_index"))
        self.assertEqual(PHASE_CLARIFY, state.get("active_phase"))

    def test_invalid_feature_entry_returns_error(self) -> None:
        ws = Path(tempfile.mkdtemp())
        sync = _sync(ws)
        sync.mkdir(parents=True, exist_ok=True)
        (sync / "speckit_invocation_queue.json").write_text(
            json.dumps({"items": ["not-a-dict"]}), encoding="utf-8"
        )
        _write_state(sync, self._approved_state())
        result = SpecKitExecutionMachine().run(_ctx(ws))
        self.assertEqual(MachineStatus.ERROR, result.status)
        self.assertEqual("FEATURE_INVALID", result.state)


class TestCheckpointContent(unittest.TestCase):
    """Spot-checks that checkpoints contain the right guidance."""

    def test_constitution_checkpoint_forbids_speckit_invocation(self) -> None:
        ws = Path(tempfile.mkdtemp())
        _write_queue(_sync(ws), [_feature()])
        result = SpecKitExecutionMachine().run(_ctx(ws))
        assert result.checkpoint is not None
        forbidden = " ".join(result.checkpoint.forbidden_actions)
        self.assertIn("SpecKit", forbidden)

    def test_tasks_checkpoint_forbids_implementation_before_approval(self) -> None:
        ws = Path(tempfile.mkdtemp())
        _write_queue(_sync(ws), [_feature()])
        _write_state(_sync(ws), {"constitution_approved": True, "active_feature_index": 0, "active_phase": PHASE_TASKS})
        result = SpecKitExecutionMachine().run(_ctx(ws))
        assert result.checkpoint is not None
        forbidden = " ".join(result.checkpoint.forbidden_actions)
        self.assertIn("app code", forbidden)

    def test_clarify_checkpoint_references_feature_name(self) -> None:
        ws = Path(tempfile.mkdtemp())
        _write_queue(_sync(ws), [_feature("feat-001", "My Feature")])
        _write_state(_sync(ws), {"constitution_approved": True, "active_feature_index": 0, "active_phase": PHASE_CLARIFY})
        result = SpecKitExecutionMachine().run(_ctx(ws))
        assert result.checkpoint is not None
        self.assertIn("My Feature", result.checkpoint.blocking_reason)


if __name__ == "__main__":
    unittest.main()
