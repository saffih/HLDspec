from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from hldspec.hld_sync import (
    DONE_LEDGER_JSON,
    FINGERPRINTS_JSON,
    SYNC_REPORT_JSON,
    SYNC_REPORT_MD,
    diff_sections,
    run_sync,
    section_fingerprints,
)


def _hld(sections: dict[str, str]) -> str:
    lines = ["# Test HLD", ""]
    for anchor, body in sections.items():
        lines += [f"## {anchor} - Section {anchor}", "", body, ""]
    return "\n".join(lines)


def _write_workspace(workspace: Path, sections: dict[str, str], specs: list[dict] | None = None) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "HLD.md").write_text(_hld(sections), encoding="utf-8")
    if specs is not None:
        sync = workspace / ".specify" / "sync"
        sync.mkdir(parents=True, exist_ok=True)
        bundles = [
            {
                "bundle_id": spec["feature_id"],
                "bundle_slug": spec["short_name"],
                "prompt_paths": {},
                "included_specs": [spec],
            }
            for spec in specs
        ]
        (sync / "speckit_bundle_queue.json").write_text(json.dumps({"bundles": bundles}), encoding="utf-8")


def _touch_spec(speckit_root: Path, short_name: str, *files: str) -> None:
    spec_dir = speckit_root / short_name
    spec_dir.mkdir(parents=True, exist_ok=True)
    for name in files:
        (spec_dir / name).write_text("content", encoding="utf-8")


def _verify_spec(speckit_root: Path, short_name: str, *phases: str) -> None:
    spec_dir = speckit_root / short_name
    spec_dir.mkdir(parents=True, exist_ok=True)
    for phase in phases:
        (spec_dir / f"{phase}_validation.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")


SPEC_001 = {"feature_id": "001", "short_name": "001-core", "source_hld_sections": ["HLD-001"]}
SPEC_002 = {"feature_id": "002", "short_name": "002-edge", "source_hld_sections": ["HLD-002"]}


class SectionFingerprintTests(unittest.TestCase):
    def test_fingerprints_one_hash_per_section(self):
        fp = section_fingerprints(_hld({"HLD-001": "alpha", "HLD-002": "beta"}))
        self.assertEqual({"HLD-001", "HLD-002"}, set(fp))
        self.assertTrue(all(len(sha) == 64 for sha in fp.values()))

    def test_diff_reports_only_the_edited_section(self):
        old = section_fingerprints(_hld({"HLD-001": "alpha", "HLD-002": "beta"}))
        new = section_fingerprints(_hld({"HLD-001": "alpha", "HLD-002": "beta CHANGED"}))
        diff = diff_sections(old, new)
        self.assertEqual(["HLD-002"], diff["changed"])
        self.assertEqual(["HLD-001"], diff["unchanged"])
        self.assertEqual([], diff["added"])
        self.assertEqual([], diff["removed"])

    def test_diff_reports_added_and_removed(self):
        old = section_fingerprints(_hld({"HLD-001": "alpha"}))
        new = section_fingerprints(_hld({"HLD-002": "beta"}))
        diff = diff_sections(old, new)
        self.assertEqual(["HLD-002"], diff["added"])
        self.assertEqual(["HLD-001"], diff["removed"])


class RunSyncTests(unittest.TestCase):
    def test_unassessable_without_working_hld(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            report = run_sync(workspace, Path(tmp) / "specs")
            self.assertEqual("UNASSESSABLE", report["status"])

    def test_done_spec_recorded_then_stale_after_section_edit(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "specs"
            _write_workspace(workspace, {"HLD-001": "alpha", "HLD-002": "beta"}, [SPEC_001, SPEC_002])
            _touch_spec(speckit_root, "001-core", "spec.md", "plan.md", "tasks.md")
            _verify_spec(speckit_root, "001-core", "specify", "plan", "tasks")

            first = run_sync(workspace, speckit_root)
            rows = {row["short_name"]: row for row in first["specs"]}
            self.assertEqual("DONE_VERIFIED", rows["001-core"]["status"])
            self.assertEqual("NOT_STARTED", rows["002-edge"]["status"])
            self.assertEqual("IN_SYNC_PENDING", first["status"])

            (workspace / "HLD.md").write_text(
                _hld({"HLD-001": "alpha CHANGED", "HLD-002": "beta"}), encoding="utf-8"
            )
            second = run_sync(workspace, speckit_root)
            rows = {row["short_name"]: row for row in second["specs"]}
            self.assertEqual("DONE_STALE", rows["001-core"]["status"])
            self.assertEqual(["HLD-001"], rows["001-core"]["stale_sections"])
            self.assertEqual("STALE_SPECS", second["status"])
            self.assertEqual(["HLD-001"], second["section_diff"]["changed"])

    def test_done_spec_with_untouched_sections_stays_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "specs"
            _write_workspace(workspace, {"HLD-001": "alpha", "HLD-002": "beta"}, [SPEC_001])
            _touch_spec(speckit_root, "001-core", "spec.md", "plan.md", "tasks.md")
            _verify_spec(speckit_root, "001-core", "specify", "plan", "tasks")

            run_sync(workspace, speckit_root)
            (workspace / "HLD.md").write_text(
                _hld({"HLD-001": "alpha", "HLD-002": "beta CHANGED"}), encoding="utf-8"
            )
            second = run_sync(workspace, speckit_root)
            self.assertEqual("DONE_VERIFIED", second["specs"][0]["status"])
            self.assertEqual("IN_SYNC", second["status"])

    def test_rebuilt_artifacts_clear_staleness(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "specs"
            _write_workspace(workspace, {"HLD-001": "alpha"}, [SPEC_001])
            _touch_spec(speckit_root, "001-core", "spec.md", "plan.md", "tasks.md")
            _verify_spec(speckit_root, "001-core", "specify", "plan", "tasks")

            run_sync(workspace, speckit_root)
            (workspace / "HLD.md").write_text(_hld({"HLD-001": "alpha CHANGED"}), encoding="utf-8")
            stale = run_sync(workspace, speckit_root)
            self.assertEqual("DONE_STALE", stale["specs"][0]["status"])

            # Rebuild the spec against the updated HLD: newer artifact mtime.
            future = time.time() + 60
            os.utime(speckit_root / "001-core" / "spec.md", (future, future))
            recovered = run_sync(workspace, speckit_root)
            self.assertEqual("DONE_VERIFIED", recovered["specs"][0]["status"])
            self.assertEqual("IN_SYNC", recovered["status"])

    def test_rebuild_older_than_hld_edit_stays_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "specs"
            _write_workspace(workspace, {"HLD-001": "alpha"}, [SPEC_001])
            _touch_spec(speckit_root, "001-core", "spec.md", "plan.md", "tasks.md")
            _verify_spec(speckit_root, "001-core", "specify", "plan", "tasks")

            run_sync(workspace, speckit_root)

            # Artifacts rebuilt at t+60, but the HLD edited later at t+120:
            # the rebuild targeted the pre-edit HLD and must stay stale.
            now = time.time()
            os.utime(speckit_root / "001-core" / "spec.md", (now + 60, now + 60))
            (workspace / "HLD.md").write_text(_hld({"HLD-001": "alpha CHANGED"}), encoding="utf-8")
            os.utime(workspace / "HLD.md", (now + 120, now + 120))

            second = run_sync(workspace, speckit_root)
            self.assertEqual("DONE_STALE", second["specs"][0]["status"])
            self.assertEqual("STALE_SPECS", second["status"])

    def test_removed_section_marks_spec_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "specs"
            _write_workspace(workspace, {"HLD-001": "alpha", "HLD-002": "beta"}, [SPEC_001])
            _touch_spec(speckit_root, "001-core", "spec.md", "plan.md", "tasks.md")
            _verify_spec(speckit_root, "001-core", "specify", "plan", "tasks")

            run_sync(workspace, speckit_root)
            (workspace / "HLD.md").write_text(_hld({"HLD-002": "beta"}), encoding="utf-8")
            second = run_sync(workspace, speckit_root)
            self.assertEqual("DONE_STALE", second["specs"][0]["status"])
            self.assertEqual(["HLD-001"], second["section_diff"]["removed"])

    def test_sync_never_deletes_decision_queue_and_regenerates_prompts(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "specs"
            _write_workspace(workspace, {"HLD-001": "alpha"}, [SPEC_001])
            decisions = workspace / ".specify" / "sync" / "hld_conversion_decision_queue.json"
            decisions.write_text(json.dumps({"decisions": [{"id": "D1", "answer": "yes"}]}), encoding="utf-8")

            report = run_sync(workspace, speckit_root)

            self.assertTrue(report["prompts_regenerated"])
            self.assertEqual(
                {"decisions": [{"id": "D1", "answer": "yes"}]},
                json.loads(decisions.read_text(encoding="utf-8")),
            )
            prompt = workspace / ".specify" / "sync" / "speckit_bundle_prompts" / "claude" / "001-core" / "prompt.md"
            self.assertTrue(prompt.is_file())

    def test_skips_prompt_regeneration_without_bundle_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            _write_workspace(workspace, {"HLD-001": "alpha"})
            report = run_sync(workspace, Path(tmp) / "specs")
            self.assertFalse(report["prompts_regenerated"])

    def test_writes_report_fingerprint_and_ledger_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "specs"
            _write_workspace(workspace, {"HLD-001": "alpha"}, [SPEC_001])
            _touch_spec(speckit_root, "001-core", "spec.md", "plan.md", "tasks.md")
            _verify_spec(speckit_root, "001-core", "specify", "plan", "tasks")

            run_sync(workspace, speckit_root)

            # The queue lives in .specify/sync, so the execution sync dir
            # selector resolves there.
            sync = workspace / ".specify" / "sync"
            for name in (FINGERPRINTS_JSON, DONE_LEDGER_JSON, SYNC_REPORT_JSON, SYNC_REPORT_MD):
                self.assertTrue((sync / name).is_file(), name)
            ledger = json.loads((sync / DONE_LEDGER_JSON).read_text(encoding="utf-8"))
            self.assertIn("001-core", ledger["specs"])
            self.assertIn("HLD-001", ledger["specs"]["001-core"]["sections"])

    def test_presence_only_spec_is_not_recorded_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            speckit_root = Path(tmp) / "specs"
            _write_workspace(workspace, {"HLD-001": "alpha"}, [SPEC_001])
            _touch_spec(speckit_root, "001-core", "spec.md", "plan.md", "tasks.md")

            report = run_sync(workspace, speckit_root)

            self.assertEqual("IN_SYNC_PENDING", report["status"])
            self.assertEqual("ACTION", report["specs"][0]["status"])
            sync = workspace / ".specify" / "sync"
            ledger = json.loads((sync / DONE_LEDGER_JSON).read_text(encoding="utf-8"))
            self.assertNotIn("001-core", ledger["specs"])


if __name__ == "__main__":
    unittest.main()
