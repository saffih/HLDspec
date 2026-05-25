from __future__ import annotations

import json
import stat
import tempfile
import unittest
from pathlib import Path

from hldspec.event_log import read_events
from hldspec.machines.project import ProjectMachine
from hldspec.state_machine import MachineContext, MachineStatus


def _make_fake_repo_with_stop_checkpoint() -> Path:
    """Minimal repo that produces a STOP_CHECKPOINT at HLD_CONVERSION_DECISIONS."""
    repo = Path(tempfile.mkdtemp())
    scripts = repo / "scripts"
    scripts.mkdir()

    # project_first_run.sh — creates workspace + queue with TBD question, exits 2
    (scripts / "project_first_run.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        'src="$1"; work="$2"\n'
        'mkdir -p "$work/.specify/sync"\n'
        'cp "$src" "$work/HLD.md"\n'
        "cat > \"$work/.specify/sync/hld_conversion_decision_queue.json\" <<'JSON'\n"
        '{"questions":[{"question_id":"Q-001","source_candidate_id":"HLD-001",'
        '"title":"Test","question":"Keep?","options":["KEEP","SPLIT"],'
        '"human_decision":"TBD","blocking":true}]}\n'
        "JSON\n"
        "exit 2\n",
        encoding="utf-8",
    )

    for file in scripts.iterdir():
        file.chmod(file.stat().st_mode | stat.S_IEXEC)

    return repo


class TestEventLogWiring(unittest.TestCase):
    def _run_to_stop_checkpoint(self):
        repo = _make_fake_repo_with_stop_checkpoint()
        source = repo / "HLD.md"
        source.write_text("# Raw HLD\n\n## Milestones\n\nBody.\n", encoding="utf-8")
        workspace = repo / ".hldspec-v2-run"

        result = ProjectMachine().run(
            MachineContext(repo_root=str(repo), source_hld=str(source), workspace=str(workspace))
        )
        log_path = workspace / ".specify" / "sync" / "hldspec_event_log.jsonl"
        return result, log_path

    def test_event_written_after_machine_completes(self):
        result, log_path = self._run_to_stop_checkpoint()

        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        self.assertTrue(log_path.exists(), f"Expected event log at {log_path}")
        events = read_events(log_path)
        self.assertGreater(len(events), 0, "Expected at least one event in the log")

    def test_event_has_required_fields(self):
        result, log_path = self._run_to_stop_checkpoint()

        events = read_events(log_path)
        for event in events:
            self.assertTrue(event.event_id, f"event_id missing on {event}")
            self.assertTrue(event.timestamp, f"timestamp missing on {event}")
            self.assertTrue(event.machine, f"machine missing on {event}")
            self.assertIsInstance(event.from_state, str, f"from_state not str on {event}")
            self.assertIsInstance(event.to_state, str, f"to_state not str on {event}")
            self.assertTrue(event.event, f"event field missing on {event}")

    def test_pipeline_halted_event_on_stop_checkpoint(self):
        result, log_path = self._run_to_stop_checkpoint()

        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        events = read_events(log_path)
        terminal_events = [e for e in events if e.event == "pipeline_halted"]
        self.assertGreater(len(terminal_events), 0, "Expected a pipeline_halted event")


if __name__ == "__main__":
    unittest.main()
