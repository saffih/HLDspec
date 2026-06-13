from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from hldspec import refresh_target as rt
from hldspec import next_feature_agents_md as nfa


def _git(target: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(target), *argv],
        text=True,
        capture_output=True,
        check=True,
    )


class RefreshTargetTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-refresh-target-")
        self.target = Path(self._tmp.name)
        _git(self.target, "init", "-q")
        _git(self.target, "config", "user.email", "test@example.com")
        _git(self.target, "config", "user.name", "Test")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _agents_md_path(self) -> Path:
        sync = rt.control_paths.resolve_control_sync_dir(self.target, create=False)
        return sync / nfa.BOOTSTRAP_FILE

    def _constitution_path(self) -> Path:
        return self.target / rt.CONSTITUTION_RELPATH

    # 1. dry-run makes no writes.
    def test_dry_run_makes_no_writes(self) -> None:
        plan = rt.refresh_target(self.target, apply=False)
        self.assertEqual(plan["mode"], "DRY_RUN")
        self.assertFalse(self._agents_md_path().exists())
        self.assertFalse(self._constitution_path().exists())
        self.assertGreater(len(plan["planned_updates"]), 0)

    # 2. apply creates missing HLDspec helper file.
    def test_apply_creates_missing_agents_md(self) -> None:
        result = rt.refresh_target(self.target, apply=True)
        self.assertEqual(result["mode"], "APPLIED")
        path = self._agents_md_path()
        self.assertTrue(path.is_file())
        self.assertIn(str(path.relative_to(self.target)), result["written_files"])

    # 3. apply updates HLDspec-owned helper file.
    def test_apply_updates_existing_agents_md(self) -> None:
        rt.refresh_target(self.target, apply=True)
        path = self._agents_md_path()
        path.write_text("stale content", encoding="utf-8")

        result = rt.refresh_target(self.target, apply=True)

        self.assertIn(str(path.relative_to(self.target)), result["written_files"])
        self.assertNotEqual(path.read_text(encoding="utf-8"), "stale content")
        self.assertIn("Next feature", path.read_text(encoding="utf-8"))

    # 4. missing constitution can be created safely.
    def test_apply_creates_missing_constitution(self) -> None:
        result = rt.refresh_target(self.target, apply=True)

        path = self._constitution_path()
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn(rt.MANAGED_BEGIN, text)
        self.assertIn(rt.MANAGED_END, text)
        self.assertIn(str(rt.CONSTITUTION_RELPATH), result["written_files"])
        self.assertEqual(result["constitution_status"]["classification"], rt.MISSING_CAN_CREATE)

    # 5. unchanged/managed constitution can be updated safely.
    def test_apply_refreshes_managed_constitution_preserving_project_rules(self) -> None:
        path = self._constitution_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        project_rule = "## Project-Specific Rules\n\n- Always use widgets, never gadgets.\n"
        path.write_text(f"# Project Constitution\n\n{rt.managed_block()}\n\n{project_rule}", encoding="utf-8")

        plan = rt.build_refresh_plan(self.target)
        self.assertEqual(plan["constitution_status"]["classification"], rt.OWNED_BY_SPECKIT_SAFE_TO_REFRESH)

        result = rt.refresh_target(self.target, apply=True)

        text = path.read_text(encoding="utf-8")
        self.assertIn("Always use widgets, never gadgets.", text)
        self.assertIn(rt.MANAGED_BEGIN, text)
        self.assertIn(rt.MANAGED_END, text)
        backup = path.with_name(path.name + rt.CONSTITUTION_BACKUP_SUFFIX)
        self.assertTrue(backup.is_file())
        self.assertIn(str(backup.relative_to(self.target)), result["backup_files"])

        # Re-running is idempotent: project rules still preserved, still classified safe-to-refresh.
        plan2 = rt.build_refresh_plan(self.target)
        self.assertEqual(plan2["constitution_status"]["classification"], rt.OWNED_BY_SPECKIT_SAFE_TO_REFRESH)
        rt.refresh_target(self.target, apply=True)
        self.assertIn("Always use widgets, never gadgets.", path.read_text(encoding="utf-8"))

    # 6. edited constitution is not overwritten and is reported as review-required.
    def test_unmanaged_constitution_is_not_overwritten(self) -> None:
        path = self._constitution_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        custom_text = "# Our Project Constitution\n\nHand-written rules, no HLDspec markers here.\n"
        path.write_text(custom_text, encoding="utf-8")

        plan = rt.build_refresh_plan(self.target)
        self.assertEqual(plan["constitution_status"]["classification"], rt.EXISTS_WITH_LOCAL_CHANGES_REQUIRES_REVIEW)
        self.assertEqual(len(plan["conflict_files"]), 1)

        result = rt.refresh_target(self.target, apply=True)

        self.assertEqual(path.read_text(encoding="utf-8"), custom_text)
        self.assertNotIn(str(rt.CONSTITUTION_RELPATH), result["written_files"])
        self.assertTrue(result["review_files"])
        review_path = self.target / result["review_files"][0]
        self.assertTrue(review_path.is_file())
        self.assertIn(rt.MANAGED_BEGIN, review_path.read_text(encoding="utf-8"))

    # 7. existing unowned file is not overwritten.
    def test_unowned_file_is_left_untouched(self) -> None:
        sync = rt.control_paths.resolve_control_sync_dir(self.target, create=True)
        other = sync / "some_other_file.md"
        other.write_text("do not touch", encoding="utf-8")

        result = rt.refresh_target(self.target, apply=True)

        self.assertEqual(other.read_text(encoding="utf-8"), "do not touch")
        self.assertNotIn(str(other.relative_to(self.target)), result["written_files"])

    # 8. existing specs/<branch>/spec.md, plan.md, tasks.md are not modified.
    def test_spec_progress_artifacts_are_not_modified(self) -> None:
        spec_dir = self.target / "specs" / "001-feature"
        spec_dir.mkdir(parents=True)
        artifacts = {}
        for name in ("spec.md", "plan.md", "tasks.md"):
            text = f"# {name}\n\noriginal content\n"
            (spec_dir / name).write_text(text, encoding="utf-8")
            artifacts[name] = text

        rt.refresh_target(self.target, apply=True)

        for name, text in artifacts.items():
            self.assertEqual((spec_dir / name).read_text(encoding="utf-8"), text)

    # 9. dirty target repo is not reset/stashed/cleaned.
    def test_dirty_target_is_not_reset_or_cleaned(self) -> None:
        dirty_file = self.target / "src_file.txt"
        dirty_file.write_text("work in progress", encoding="utf-8")

        plan = rt.build_refresh_plan(self.target)
        self.assertTrue(plan["git_dirty"])

        rt.refresh_target(self.target, apply=True)

        self.assertEqual(dirty_file.read_text(encoding="utf-8"), "work in progress")
        status = _git(self.target, "status", "--porcelain").stdout
        self.assertIn("src_file.txt", status)

    # 10. product files are never touched.
    def test_product_files_are_never_touched(self) -> None:
        product_file = self.target / "src" / "app.py"
        product_file.parent.mkdir(parents=True)
        product_text = "def main():\n    pass\n"
        product_file.write_text(product_text, encoding="utf-8")

        result = rt.refresh_target(self.target, apply=True)

        self.assertEqual(product_file.read_text(encoding="utf-8"), product_text)
        self.assertNotIn(str(product_file.relative_to(self.target)), result["written_files"])

    # 11. refresh output reports skipped/conflict files.
    def test_output_reports_skipped_and_conflict_files(self) -> None:
        path = self._constitution_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Hand-written constitution, no markers\n", encoding="utf-8")

        plan = rt.build_refresh_plan(self.target)

        self.assertIn("skipped_files", plan)
        self.assertIn("conflict_files", plan)
        self.assertEqual(len(plan["conflict_files"]), 1)
        self.assertEqual(plan["conflict_files"][0]["path"], str(rt.CONSTITUTION_RELPATH))

    # 12. "speckit status" wording maps to full run card/gap evaluation.
    def test_run_card_pointer_points_to_status_driver(self) -> None:
        plan = rt.build_refresh_plan(self.target)
        pointer = plan["run_card_pointer"]
        self.assertIn("speckit status", pointer)
        self.assertIn("SpecKit run card", pointer)
        self.assertIn("next_feature_readiness_report.py", pointer)


if __name__ == "__main__":
    unittest.main()
