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


def _touch(root: Path, short_name: str, *files: str) -> None:
    spec_dir = root / short_name
    spec_dir.mkdir(parents=True, exist_ok=True)
    for name in files:
        (spec_dir / name).write_text("content", encoding="utf-8")


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
            self.assertEqual("DONE", result["phases"]["specify"])
            self.assertEqual("PENDING", result["phases"]["plan"])
            self.assertEqual("PENDING_PLAN", result["status"])

    def test_done_when_all_artifacts_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _touch(root, "027-scope", "spec.md", "plan.md", "tasks.md")
            result = assess_spec(root, "027-scope")
            self.assertEqual("DONE", result["status"])

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
        self.assertEqual("tasks", first_pending_phase({"specify": "DONE", "plan": "DONE", "tasks": "PENDING"}))
        self.assertIsNone(first_pending_phase({"specify": "DONE", "plan": "DONE", "tasks": "DONE"}))


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
            _touch(speckit_root, "029-integration", "spec.md")
            state = build_execution_state(workspace, speckit_root)
            self.assertEqual("IN_PROGRESS", state["status"])
            self.assertEqual("029", state["resume"]["feature_id"])
            self.assertEqual("plan", state["resume"]["phase"])

    def test_all_tasks_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "specs"
            _write_queue(workspace, [_bundle("G01", "g01", [("027", "027-scope")])])
            _touch(speckit_root, "027-scope", "spec.md", "plan.md", "tasks.md")
            state = build_execution_state(workspace, speckit_root)
            self.assertEqual("ALL_TASKS_DONE", state["status"])


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
