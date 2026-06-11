from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec.command_runner import CommandResult
from hldspec.speckit_drive_loop import parse_bundle_report, run_drive_loop


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


def _touch(root: Path, short_name: str, *files: str) -> None:
    spec_dir = root / short_name
    spec_dir.mkdir(parents=True, exist_ok=True)
    for name in files:
        (spec_dir / name).write_text("content", encoding="utf-8")


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


class RunDriveLoopTests(unittest.TestCase):
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

            runner = FakeRunner(speckit_root, [])

            summary = run_drive_loop(workspace, speckit_root, runner=runner, agent_cmd="claude")

            self.assertEqual("NO_BUNDLES", summary["stop_reason"])

    def test_stops_unassessable_when_speckit_root_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "nonexistent"
            _write_queue(workspace, [_bundle("G01", "g01", [("027", "027-scope")])])
            _write_prompt(workspace, "g01")

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

            run_drive_loop(workspace, speckit_root, runner=FakeRunner(speckit_root, []), agent_cmd="claude")

            sync = workspace / ".specify" / "sync"
            self.assertTrue((sync / "speckit_drive_loop_report.json").exists())
            self.assertTrue((sync / "speckit_drive_loop_report.md").exists())


if __name__ == "__main__":
    unittest.main()
