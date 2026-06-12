from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec.speckit_execution_state import (
    assess_spec,
    build_execution_state,
    first_pending_phase,
    next_action,
    write_execution_state,
)


def _bundle(bundle_id: str, slug: str, specs: list[tuple[str, str]]) -> dict:
    return {
        "bundle_id": bundle_id,
        "bundle_slug": slug,
        "prompt_paths": {
            "claude": f".specify/sync/speckit_bundle_prompts/claude/{slug}/prompt.md",
            "codex": f".specify/sync/speckit_bundle_prompts/codex/{slug}/prompt.md",
        },
        "included_specs": [
            {"feature_id": fid, "short_name": short} for fid, short in specs
        ],
    }


def _write_queue(workspace: Path, bundles: list[dict]) -> None:
    sync = workspace / ".specify" / "sync"
    sync.mkdir(parents=True, exist_ok=True)
    (sync / "speckit_bundle_queue.json").write_text(json.dumps({"bundles": bundles}), encoding="utf-8")


def _write_canonical_invocation_queue(workspace: Path, items: list[dict]) -> None:
    sync = workspace / ".hldspec" / "sync"
    sync.mkdir(parents=True, exist_ok=True)
    (sync / "speckit_invocation_queue.json").write_text(json.dumps({"items": items}), encoding="utf-8")


def _touch(root: Path, short_name: str, *files: str) -> None:
    spec_dir = root / short_name
    spec_dir.mkdir(parents=True, exist_ok=True)
    for name in files:
        (spec_dir / name).write_text("content", encoding="utf-8")


def _verify(root: Path, short_name: str, *phases: str, status: str = "PASS") -> None:
    spec_dir = root / short_name
    spec_dir.mkdir(parents=True, exist_ok=True)
    for phase in phases:
        (spec_dir / f"{phase}_validation.json").write_text(json.dumps({"status": status}), encoding="utf-8")


class AssessSpecTests(unittest.TestCase):
    def test_not_started_when_dir_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = assess_spec(Path(tmp), "027-scope")
            self.assertFalse(result["exists"])
            self.assertEqual("NOT_STARTED", result["status"])

    def test_pending_when_partial_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _touch(root, "027-scope", "spec.md")
            result = assess_spec(root, "027-scope")
            self.assertEqual("PRESENT_UNVERIFIED", result["phases"]["specify"])
            self.assertEqual("PENDING", result["phases"]["plan"])
            self.assertEqual("ACTION", result["status"])

    def test_done_verified_when_all_artifacts_have_passing_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _touch(root, "027-scope", "spec.md", "plan.md", "tasks.md")
            _verify(root, "027-scope", "specify", "plan", "tasks")
            result = assess_spec(root, "027-scope")
            self.assertEqual("DONE_VERIFIED", result["status"])

    def test_fail_json_blocks_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _touch(root, "027-scope", "spec.md")
            _verify(root, "027-scope", "specify", status="FAIL")
            result = assess_spec(root, "027-scope")
            self.assertEqual("BLOCKED", result["phases"]["specify"])
            self.assertEqual("BLOCKED", result["status"])

    def test_empty_file_is_not_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec_dir = root / "027-scope"
            spec_dir.mkdir(parents=True)
            (spec_dir / "spec.md").write_text("", encoding="utf-8")
            result = assess_spec(root, "027-scope")
            self.assertEqual("PENDING", result["phases"]["specify"])

    def test_first_pending_phase(self) -> None:
        self.assertEqual("specify", first_pending_phase({"specify": "PENDING", "plan": "PENDING", "tasks": "PENDING"}))
        self.assertEqual("tasks", first_pending_phase({"specify": "DONE_VERIFIED", "plan": "DONE_VERIFIED", "tasks": "PENDING"}))
        self.assertIsNone(first_pending_phase({"specify": "DONE_VERIFIED", "plan": "DONE_VERIFIED", "tasks": "DONE_VERIFIED"}))


class BuildExecutionStateTests(unittest.TestCase):
    def test_unknown_when_speckit_root_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            _write_queue(workspace, [_bundle("G01", "g01", [("027", "027-scope")])])
            state = build_execution_state(workspace, Path(tmp) / "nonexistent")
            self.assertEqual("UNKNOWN", state["status"])
            self.assertIsNone(state["resume"])

    def test_resume_points_at_first_incomplete_spec(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "specs"
            _write_queue(
                workspace,
                [
                    _bundle("G01", "g01", [("027", "027-scope"), ("029", "029-integration")]),
                    _bundle("G02", "g02", [("008", "008-overview")]),
                ],
            )
            # 027 fully done; 029 has specify only -> resume at 029/plan
            _touch(speckit_root, "027-scope", "spec.md", "plan.md", "tasks.md")
            _verify(speckit_root, "027-scope", "specify", "plan", "tasks")
            _touch(speckit_root, "029-integration", "spec.md")
            state = build_execution_state(workspace, speckit_root)
            self.assertEqual("IN_PROGRESS", state["status"])
            self.assertEqual("029", state["resume"]["feature_id"])
            self.assertEqual("specify", state["resume"]["phase"])

    def test_canonical_invocation_queue_is_assessable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "specs"
            _write_canonical_invocation_queue(
                workspace,
                [{"feature_id": "F01", "short_name": "001-flow", "prompt_paths": {"codex": "prompt.md"}}],
            )
            _touch(speckit_root, "001-flow", "spec.md")

            state = build_execution_state(workspace, speckit_root)

            self.assertEqual("IN_PROGRESS", state["status"])
            self.assertEqual("F01", state["resume"]["feature_id"])
            self.assertEqual("specify", state["resume"]["phase"])
            self.assertEqual("prompt.md", state["resume"]["prompt_paths"]["codex"])

    def test_all_tasks_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "specs"
            _write_queue(workspace, [_bundle("G01", "g01", [("027", "027-scope")])])
            _touch(speckit_root, "027-scope", "spec.md", "plan.md", "tasks.md")
            _verify(speckit_root, "027-scope", "specify", "plan", "tasks")
            state = build_execution_state(workspace, speckit_root)
            self.assertEqual("ALL_TASKS_DONE", state["status"])

    def test_presence_only_all_artifacts_is_not_all_tasks_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "specs"
            _write_queue(workspace, [_bundle("G01", "g01", [("027", "027-scope")])])
            _touch(speckit_root, "027-scope", "spec.md", "plan.md", "tasks.md")
            state = build_execution_state(workspace, speckit_root)
            self.assertEqual("IN_PROGRESS", state["status"])
            self.assertEqual("specify", state["resume"]["phase"])

    def test_write_execution_state_does_not_overwrite_machine_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "specs"
            _write_canonical_invocation_queue(workspace, [{"feature_id": "F01", "short_name": "001-flow"}])
            sync = workspace / ".hldspec" / "sync"
            machine_state = sync / "speckit_execution_state.json"
            machine_state.write_text('{"state_version":2,"active_phase":"PLAN"}\n', encoding="utf-8")
            _touch(speckit_root, "001-flow", "spec.md")

            write_execution_state(workspace, speckit_root)

            self.assertEqual('{"state_version":2,"active_phase":"PLAN"}\n', machine_state.read_text(encoding="utf-8"))
            self.assertTrue((sync / "speckit_execution_assessment.json").is_file())
            self.assertTrue((sync / "speckit_execution_assessment.md").is_file())


class NextActionTests(unittest.TestCase):
    def test_unknown_yields_do_it_all_exit3(self) -> None:
        action = next_action({"status": "UNKNOWN", "bundles": [_bundle("G01", "g01", [("027", "027-scope")])]})
        self.assertEqual(3, action["exit_code"])
        self.assertEqual("DO_IT_ALL", action["mode"])
        self.assertEqual(1, len(action["ordered_prompts"]))

    def test_all_tasks_done_yields_implement_gate_exit2(self) -> None:
        action = next_action({"status": "ALL_TASKS_DONE", "bundles": []})
        self.assertEqual(2, action["exit_code"])
        self.assertEqual("IMPLEMENT_GATE", action["mode"])

    def test_in_progress_yields_continue_exit0_with_runtime_prompt(self) -> None:
        payload = {
            "status": "IN_PROGRESS",
            "bundles": [_bundle("G01", "g01", [("027", "027-scope")])],
            "resume": {
                "bundle_id": "G01",
                "feature_id": "027",
                "phase": "plan",
                "prompt_paths": {"claude": "claude/path.md", "codex": "codex/path.md"},
            },
        }
        action = next_action(payload, runtime="codex")
        self.assertEqual(0, action["exit_code"])
        self.assertEqual("CONTINUE", action["mode"])
        self.assertEqual("codex/path.md", action["bundle_prompt"])


if __name__ == "__main__":
    unittest.main()
