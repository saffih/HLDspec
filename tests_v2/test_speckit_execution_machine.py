"""Tests for SpecKitExecutionMachine.

Covers:
- Missing inputs (no workspace, no queue, invalid queue)
- Constitution phase: pending, decision-in-state → continue, already approved
- Feature phases: SPECIFY/PLAN/TASKS/IMPLEMENT pending, COMPLETE → advance phase, DONE → advance feature
- Completion: all features done
- State is written correctly across transitions
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec.machines.speckit_execution import (
    PHASE_ANALYZE,
    PHASE_CHECKLIST,
    PHASE_CLARIFY,
    PHASE_DONE,
    PHASE_IMPLEMENT,
    PHASE_PLAN,
    PHASE_SPECIFY,
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

    def test_specify_pending_produces_checkpoint(self) -> None:
        ws = Path(tempfile.mkdtemp())
        _write_queue(_sync(ws), [_feature()])
        _write_state(_sync(ws), self._approved_state(active_phase=PHASE_SPECIFY))
        result = SpecKitExecutionMachine().run(_ctx(ws))
        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        self.assertEqual("SPECIFY_PENDING", result.state)
        assert result.checkpoint is not None
        self.assertTrue(result.checkpoint.has_open_questions())

    def test_specify_default_phase_is_used_when_not_set(self) -> None:
        """active_phase defaults to SPECIFY when missing from state."""
        ws = Path(tempfile.mkdtemp())
        _write_queue(_sync(ws), [_feature()])
        _write_state(_sync(ws), {"constitution_approved": True, "active_feature_index": 0})
        result = SpecKitExecutionMachine().run(_ctx(ws))
        self.assertEqual("SPECIFY_PENDING", result.state)

    def test_specify_complete_advances_to_clarify(self) -> None:
        ws = Path(tempfile.mkdtemp())
        feat = _feature("feat-001")
        _write_queue(_sync(ws), [feat])
        _write_state(_sync(ws), {**self._approved_state(active_phase=PHASE_SPECIFY), **{"feat-001_SPECIFY_decision": "COMPLETE"}})
        result = SpecKitExecutionMachine().run(_ctx(ws))
        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("SPECIFY_COMPLETE", result.state)
        self.assertEqual(PHASE_CLARIFY, _read_state(_sync(ws)).get("active_phase"))

    def test_plan_pending_produces_checkpoint(self) -> None:
        ws = Path(tempfile.mkdtemp())
        _write_queue(_sync(ws), [_feature()])
        _write_state(_sync(ws), self._approved_state(active_phase=PHASE_PLAN))
        result = SpecKitExecutionMachine().run(_ctx(ws))
        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        self.assertEqual("PLAN_PENDING", result.state)

    def test_plan_complete_advances_to_checklist(self) -> None:
        ws = Path(tempfile.mkdtemp())
        feat = _feature("feat-001")
        _write_queue(_sync(ws), [feat])
        _write_state(_sync(ws), {**self._approved_state(active_phase=PHASE_PLAN), **{"feat-001_PLAN_decision": "COMPLETE"}})
        result = SpecKitExecutionMachine().run(_ctx(ws))
        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("PLAN_COMPLETE", result.state)
        self.assertEqual(PHASE_CHECKLIST, _read_state(_sync(ws)).get("active_phase"))

    def test_tasks_pending_produces_checkpoint(self) -> None:
        ws = Path(tempfile.mkdtemp())
        _write_queue(_sync(ws), [_feature()])
        _write_state(_sync(ws), self._approved_state(active_phase=PHASE_TASKS))
        result = SpecKitExecutionMachine().run(_ctx(ws))
        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        self.assertEqual("TASKS_PENDING", result.state)

    def test_tasks_complete_advances_to_analyze(self) -> None:
        ws = Path(tempfile.mkdtemp())
        feat = _feature("feat-001")
        _write_queue(_sync(ws), [feat])
        _write_state(_sync(ws), {**self._approved_state(active_phase=PHASE_TASKS), **{"feat-001_TASKS_decision": "COMPLETE"}})
        result = SpecKitExecutionMachine().run(_ctx(ws))
        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("TASKS_COMPLETE", result.state)
        self.assertEqual(PHASE_ANALYZE, _read_state(_sync(ws)).get("active_phase"))

    def test_implement_complete_advances_to_done(self) -> None:
        ws = Path(tempfile.mkdtemp())
        feat = _feature("feat-001")
        _write_queue(_sync(ws), [feat])
        _write_state(_sync(ws), {**self._approved_state(active_phase=PHASE_IMPLEMENT), **{"feat-001_IMPLEMENT_decision": "COMPLETE"}})
        result = SpecKitExecutionMachine().run(_ctx(ws))
        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("IMPLEMENT_COMPLETE", result.state)
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
        self.assertEqual(PHASE_SPECIFY, state.get("active_phase"))

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


class _FakeInvoker:
    """Records invocations; reports artifacts produced per the `produced` flag."""

    def __init__(self, produced=True, ok=True):
        self.produced = produced
        self.ok = ok
        self.calls = []

    def invoke(self, phase, prompt):
        self.calls.append((phase, prompt))
        from hldspec.speckit_invoker import InvocationResult

        return InvocationResult(
            phase=phase, skill=f"speckit-{phase.lower()}", returncode=0 if self.ok else 1,
            ok=self.ok, stdout="", stderr="", produced_artifacts=self.produced,
        )


class TestLiveMode(unittest.TestCase):
    """Live mode actually invokes SpecKit and gates on produced artifacts."""

    def test_live_constitution_invokes_and_advances_when_artifact_produced(self):
        ws = Path(tempfile.mkdtemp())
        _write_queue(_sync(ws), [_feature()])
        inv = _FakeInvoker(produced=True)
        result = SpecKitExecutionMachine(invoker=inv).run(_ctx(ws))
        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("CONSTITUTION_APPROVED", result.state)
        self.assertEqual(inv.calls[0][0], "CONSTITUTION")

    def test_live_blocks_on_hollow_completion(self):
        """exit 0 but no artifact => blocked, not advanced."""
        ws = Path(tempfile.mkdtemp())
        _write_queue(_sync(ws), [_feature()])
        inv = _FakeInvoker(produced=False, ok=True)
        result = SpecKitExecutionMachine(invoker=inv).run(_ctx(ws))
        self.assertEqual(MachineStatus.BLOCKED, result.status)
        self.assertIn("hollow completion", result.checkpoint.blocking_reason.lower())

    def test_live_ignores_stale_simulated_state(self):
        """A prior simulated run's all_complete must not short-circuit live mode."""
        ws = Path(tempfile.mkdtemp())
        _write_queue(_sync(ws), [_feature()])
        # Stale state: no state_version, marked all complete + past end.
        _write_state(_sync(ws), {"constitution_approved": True, "active_feature_index": 99, "all_complete": True})
        inv = _FakeInvoker(produced=True)
        result = SpecKitExecutionMachine(invoker=inv).run(_ctx(ws))
        # Should NOT be ALL_FEATURES_COMPLETE — stale state discarded, restarts at constitution.
        self.assertNotEqual("ALL_FEATURES_COMPLETE", result.state)
        self.assertEqual("CONSTITUTION_APPROVED", result.state)


def _pointer(target: Path, controller: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    (target / ".hldspec-run.json").write_text(
        json.dumps({"schema_version": 1, "controller_root": str(controller)}), encoding="utf-8"
    )


def _ctx_new(workspace: Path) -> MachineContext:
    return MachineContext(
        repo_root=str(workspace), workspace=str(workspace), metadata={"workspace_layout": "new"}
    )


class TestControlSyncPathResolution(unittest.TestCase):
    """A3.2c: SpecKitExecutionMachine must resolve its control/sync dir the
    same pointer-aware way next_feature_readiness's evidence reader does, so
    external-controller mode can't split writer/reader state.
    """

    def test_normal_mode_new_layout_writes_target_local_hldspec_sync(self) -> None:
        ws = Path(tempfile.mkdtemp())
        target_sync = ws / ".hldspec" / "sync"
        _write_queue(target_sync, [_feature()])
        _write_state(target_sync, {"constitution_decision": "APPROVED"})

        result = SpecKitExecutionMachine().run(_ctx_new(ws))

        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("CONSTITUTION_APPROVED", result.state)
        self.assertTrue(_read_state(target_sync).get("constitution_approved"))

    def test_external_controller_mode_writes_to_controller_sync(self) -> None:
        ws = Path(tempfile.mkdtemp())
        controller = Path(tempfile.mkdtemp())
        _pointer(ws, controller)
        controller_sync = controller / ".hldspec" / "sync"
        _write_queue(controller_sync, [_feature()])
        _write_state(controller_sync, {"constitution_decision": "APPROVED"})

        result = SpecKitExecutionMachine().run(_ctx_new(ws))

        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("CONSTITUTION_APPROVED", result.state)
        self.assertTrue(_read_state(controller_sync).get("constitution_approved"))
        # Nothing written into the target's own .hldspec — controller sync is
        # the single source of truth in external-controller mode.
        self.assertFalse((ws / ".hldspec").exists())

    def test_external_controller_mode_ignores_stale_target_local_sync(self) -> None:
        ws = Path(tempfile.mkdtemp())
        controller = Path(tempfile.mkdtemp())
        _pointer(ws, controller)
        # Stale target-local state from before externalization (or a bug):
        # must not be read once a controller pointer exists.
        stale_sync = ws / ".hldspec" / "sync"
        _write_queue(stale_sync, [_feature("stale-feature")])
        _write_state(stale_sync, {"constitution_decision": "APPROVED", "active_feature_index": 5})

        controller_sync = controller / ".hldspec" / "sync"
        _write_queue(controller_sync, [_feature("feat-001")])

        result = SpecKitExecutionMachine().run(_ctx_new(ws))

        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        self.assertEqual("CONSTITUTION_PENDING", result.state)
        # The stale target-local state must be untouched by this run.
        self.assertEqual(
            {"constitution_decision": "APPROVED", "active_feature_index": 5},
            _read_state(stale_sync),
        )

    def test_legacy_layout_default_unaffected_by_controller_pointer(self) -> None:
        """Existing (legacy-layout) behavior must be preserved even if a
        target somehow carries a controller pointer -- legacy layout's sync
        dir (firstrun/.specify/sync) isn't part of the .hldspec pointer
        contract, so it must keep resolving target-local exactly as before.
        """
        ws = Path(tempfile.mkdtemp())
        controller = Path(tempfile.mkdtemp())
        _pointer(ws, controller)
        _write_queue(_sync(ws), [_feature()])
        _write_state(_sync(ws), {"constitution_decision": "APPROVED"})

        result = SpecKitExecutionMachine().run(_ctx(ws))

        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("CONSTITUTION_APPROVED", result.state)
        self.assertTrue(_read_state(_sync(ws)).get("constitution_approved"))


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

    def test_specify_checkpoint_references_feature_name(self) -> None:
        ws = Path(tempfile.mkdtemp())
        _write_queue(_sync(ws), [_feature("feat-001", "My Feature")])
        _write_state(_sync(ws), {"constitution_approved": True, "active_feature_index": 0, "active_phase": PHASE_SPECIFY})
        result = SpecKitExecutionMachine().run(_ctx(ws))
        assert result.checkpoint is not None
        self.assertIn("My Feature", result.checkpoint.blocking_reason)


if __name__ == "__main__":
    unittest.main()
