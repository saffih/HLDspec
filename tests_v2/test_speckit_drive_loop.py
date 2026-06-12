from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec.command_runner import CommandResult
from hldspec.speckit_drive_loop import parse_bundle_report, prework_approved, run_drive_loop


def _bundle(bundle_id: str, slug: str, specs: list[tuple[str, str]]) -> dict:
    return {
        "bundle_id": bundle_id,
        "bundle_slug": slug,
        "prompt_paths": {
            "claude": f".specify/sync/speckit_bundle_prompts/claude/{slug}/prompt.md",
        },
        "included_specs": [{"feature_id": fid, "short_name": short} for fid, short in specs],
    }


def _write_queue(workspace: Path, bundles: list[dict]) -> None:
    sync = workspace / ".specify" / "sync"
    sync.mkdir(parents=True, exist_ok=True)
    (sync / "speckit_bundle_queue.json").write_text(json.dumps({"bundles": bundles}), encoding="utf-8")


def _write_prompt(workspace: Path, slug: str) -> None:
    path = workspace / ".specify" / "sync" / "speckit_bundle_prompts" / "claude" / slug / "prompt.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# Bundle prompt {slug}\n", encoding="utf-8")


def _write_approval(workspace: Path) -> None:
    sync = workspace / ".specify" / "sync"
    sync.mkdir(parents=True, exist_ok=True)
    (sync / "speckit_prework_approval.json").write_text(json.dumps({"status": "APPROVED"}), encoding="utf-8")


def _touch(root: Path, short_name: str, *files: str) -> None:
    spec_dir = root / short_name
    spec_dir.mkdir(parents=True, exist_ok=True)
    for name in files:
        (spec_dir / name).write_text("content", encoding="utf-8")
        phase = {"spec.md": "specify", "plan.md": "plan", "tasks.md": "tasks"}.get(name)
        if phase:
            (spec_dir / f"{phase}_validation.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")


class FakeRunner:
    """Replays canned responses; optionally touches SpecKit artifacts as a
    side effect, simulating a bundle that actually produced output."""

    def __init__(self, speckit_root: Path, responses: list[dict]):
        self.speckit_root = speckit_root
        self.responses = list(responses)
        self.calls: list[dict] = []

    def run(self, command, *, cwd=None, capture=False, input_text=None):
        self.calls.append({"command": list(command), "cwd": cwd, "input_text": input_text})
        resp = self.responses.pop(0)
        for short_name, files in resp.get("touch", []):
            _touch(self.speckit_root, short_name, *files)
        return CommandResult(
            returncode=resp.get("returncode", 0),
            command=tuple(str(c) for c in command),
            stdout=resp.get("stdout", ""),
            stderr=resp.get("stderr", ""),
        )


class ParseBundleReportTests(unittest.TestCase):
    def test_extracts_pass(self):
        report = parse_bundle_report("...\nRunSkeptic status: PASS\n...")
        self.assertEqual("PASS", report["runskeptic_status"])
        self.assertFalse(report["has_reassessment_request"])

    def test_extracts_last_status_when_multiple(self):
        text = "RunSkeptic status: PASS\n...\nRunSkeptic status: CONFLICT\n"
        report = parse_bundle_report(text)
        self.assertEqual("CONFLICT", report["runskeptic_status"])

    def test_unknown_when_absent(self):
        report = parse_bundle_report("no status here")
        self.assertEqual("UNKNOWN", report["runskeptic_status"])

    def test_detects_reassessment_request(self):
        report = parse_bundle_report("RunSkeptic status: PASS\n\nReassessment request\nBlocker type: ...")
        self.assertTrue(report["has_reassessment_request"])

    def test_echoed_template_line_cannot_produce_false_pass(self):
        # Every bundle prompt contains this literal spec line; an agent echoing
        # it after a real ACTION must not flip the last status to PASS.
        text = "RunSkeptic status: ACTION\n...\n- `RunSkeptic status: PASS | ACTION | CONFLICT`\n"
        report = parse_bundle_report(text)
        self.assertNotEqual("PASS", report["runskeptic_status"])

    def test_status_with_trailing_commentary_still_parses(self):
        report = parse_bundle_report("RunSkeptic status: PASS — all gates clean\n")
        self.assertEqual("PASS", report["runskeptic_status"])


class RunDriveLoopTests(unittest.TestCase):
    def test_refuses_to_run_without_prework_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "specs"
            _write_queue(workspace, [_bundle("G01", "g01", [("027", "027-scope")])])
            _write_prompt(workspace, "g01")
            speckit_root.mkdir(parents=True)

            runner = FakeRunner(speckit_root, [])
            summary = run_drive_loop(workspace, speckit_root, runner=runner, agent_cmd="claude")

            self.assertEqual("NOT_APPROVED", summary["stop_reason"])
            self.assertEqual([], runner.calls)

    def test_auto_continues_across_bundles_on_pass_with_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "specs"
            _write_queue(
                workspace,
                [
                    _bundle("G01", "g01", [("027", "027-scope")]),
                    _bundle("G02", "g02", [("008", "008-overview")]),
                ],
            )
            _write_prompt(workspace, "g01")
            _write_prompt(workspace, "g02")
            speckit_root.mkdir(parents=True)

            _write_approval(workspace)
            runner = FakeRunner(
                speckit_root,
                [
                    {"stdout": "RunSkeptic status: PASS\n", "touch": [("027-scope", ["spec.md", "plan.md", "tasks.md"])]},
                    {"stdout": "RunSkeptic status: PASS\n", "touch": [("008-overview", ["spec.md", "plan.md", "tasks.md"])]},
                ],
            )

            summary = run_drive_loop(workspace, speckit_root, runner=runner, agent_cmd="claude")

            self.assertEqual(2, len(summary["bundles_run"]))
            self.assertEqual("IMPLEMENT_GATE", summary["stop_reason"])
            self.assertEqual("ALL_TASKS_DONE", summary["final_state"]["status"])

    def test_stops_on_runskeptic_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "specs"
            _write_queue(workspace, [_bundle("G01", "g01", [("027", "027-scope")])])
            _write_prompt(workspace, "g01")
            speckit_root.mkdir(parents=True)

            _write_approval(workspace)
            runner = FakeRunner(speckit_root, [{"stdout": "RunSkeptic status: ACTION\n"}])

            summary = run_drive_loop(workspace, speckit_root, runner=runner, agent_cmd="claude")

            self.assertEqual(0, len(summary["bundles_run"]))
            self.assertEqual("NEEDS_ATTENTION", summary["stop_reason"])
            self.assertEqual("ACTION", summary["last_report"]["runskeptic_status"])

    def test_stops_on_reassessment_request_even_if_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "specs"
            _write_queue(workspace, [_bundle("G01", "g01", [("027", "027-scope")])])
            _write_prompt(workspace, "g01")
            speckit_root.mkdir(parents=True)

            _write_approval(workspace)
            runner = FakeRunner(
                speckit_root,
                [
                    {
                        "stdout": "RunSkeptic status: PASS\n\nReassessment request\nBlocker type: missing evidence\n",
                        "touch": [("027-scope", ["spec.md"])],
                    }
                ],
            )

            summary = run_drive_loop(workspace, speckit_root, runner=runner, agent_cmd="claude")

            self.assertEqual(0, len(summary["bundles_run"]))
            self.assertEqual("NEEDS_ATTENTION", summary["stop_reason"])

    def test_stops_on_no_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "specs"
            _write_queue(workspace, [_bundle("G01", "g01", [("027", "027-scope")])])
            _write_prompt(workspace, "g01")
            speckit_root.mkdir(parents=True)

            # PASS, but no artifacts changed -> resume pointer unchanged.
            _write_approval(workspace)
            runner = FakeRunner(speckit_root, [{"stdout": "RunSkeptic status: PASS\n"}])

            summary = run_drive_loop(workspace, speckit_root, runner=runner, agent_cmd="claude")

            self.assertEqual(0, len(summary["bundles_run"]))
            self.assertEqual("NO_PROGRESS", summary["stop_reason"])

    def test_stops_at_implement_gate_when_already_all_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "specs"
            _write_queue(workspace, [_bundle("G01", "g01", [("027", "027-scope")])])
            _write_prompt(workspace, "g01")
            _touch(speckit_root, "027-scope", "spec.md", "plan.md", "tasks.md")

            _write_approval(workspace)
            runner = FakeRunner(speckit_root, [])

            summary = run_drive_loop(workspace, speckit_root, runner=runner, agent_cmd="claude")

            self.assertEqual(0, len(summary["bundles_run"]))
            self.assertEqual("IMPLEMENT_GATE", summary["stop_reason"])
            self.assertEqual([], runner.calls)

    def test_stops_with_no_bundles_when_queue_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "specs"
            workspace.mkdir(parents=True)
            speckit_root.mkdir(parents=True)

            _write_approval(workspace)
            runner = FakeRunner(speckit_root, [])

            summary = run_drive_loop(workspace, speckit_root, runner=runner, agent_cmd="claude")

            self.assertEqual("NO_BUNDLES", summary["stop_reason"])

    def test_stops_unassessable_when_speckit_root_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "nonexistent"
            _write_queue(workspace, [_bundle("G01", "g01", [("027", "027-scope")])])
            _write_prompt(workspace, "g01")

            _write_approval(workspace)
            runner = FakeRunner(speckit_root, [])

            summary = run_drive_loop(workspace, speckit_root, runner=runner, agent_cmd="claude")

            self.assertEqual("UNASSESSABLE", summary["stop_reason"])
            self.assertEqual([], runner.calls)

    def test_writes_report_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "specs"
            _write_queue(workspace, [_bundle("G01", "g01", [("027", "027-scope")])])
            _write_prompt(workspace, "g01")
            _touch(speckit_root, "027-scope", "spec.md", "plan.md", "tasks.md")
            _write_approval(workspace)

            run_drive_loop(workspace, speckit_root, runner=FakeRunner(speckit_root, []), agent_cmd="claude")

            sync = workspace / ".specify" / "sync"
            self.assertTrue((sync / "speckit_drive_loop_report.json").exists())
            self.assertTrue((sync / "speckit_drive_loop_report.md").exists())


class ExternalControllerApprovalTests(unittest.TestCase):
    """Invariant C: approval and reports must resolve through the controller."""

    def _external_target(self, tmp: Path) -> tuple[Path, Path]:
        workspace = tmp / "ws"
        controller = tmp / "controller"
        workspace.mkdir(parents=True)
        (workspace / ".hldspec-run.json").write_text(
            json.dumps({"schema_version": 1, "controller_root": str(controller)}), encoding="utf-8"
        )
        return workspace, controller

    def test_prework_approved_reads_controller_sync_in_external_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace, controller = self._external_target(Path(tmp))
            controller_sync = controller / ".hldspec" / "sync"
            controller_sync.mkdir(parents=True)
            (controller_sync / "speckit_prework_approval.json").write_text(
                json.dumps({"status": "APPROVED"}), encoding="utf-8"
            )

            self.assertTrue(prework_approved(workspace))
            self.assertFalse((workspace / ".hldspec").exists())

    def test_prework_not_approved_when_controller_lacks_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace, controller = self._external_target(Path(tmp))
            (controller / ".hldspec" / "sync").mkdir(parents=True)

            self.assertFalse(prework_approved(workspace))

    def test_stale_target_local_approval_cannot_authorize_external_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace, controller = self._external_target(Path(tmp))
            (controller / ".hldspec" / "sync").mkdir(parents=True)
            stale = workspace / ".specify" / "sync"
            stale.mkdir(parents=True)
            (stale / "speckit_prework_approval.json").write_text(
                json.dumps({"status": "APPROVED"}), encoding="utf-8"
            )

            self.assertFalse(prework_approved(workspace))

            summary = run_drive_loop(
                workspace, Path(tmp) / "specs", runner=FakeRunner(Path(tmp) / "specs", []), agent_cmd="claude"
            )
            self.assertEqual("NOT_APPROVED", summary["stop_reason"])

    def test_drive_loop_report_lands_in_controller_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace, controller = self._external_target(Path(tmp))
            speckit_root = Path(tmp) / "specs"

            summary = run_drive_loop(
                workspace, speckit_root, runner=FakeRunner(speckit_root, []), agent_cmd="claude"
            )

            self.assertEqual("NOT_APPROVED", summary["stop_reason"])
            controller_sync = controller / ".hldspec" / "sync"
            self.assertTrue((controller_sync / "speckit_drive_loop_report.json").exists())
            self.assertFalse((workspace / ".hldspec").exists())
            self.assertFalse((workspace / ".specify").exists())


if __name__ == "__main__":
    unittest.main()
