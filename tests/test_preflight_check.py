"""PROCESS-001 — Tests for preflight_check.py.

Tests:
1. Clean tree (no issues) => safe, exit 0
2. Synthetic staged changes => UNSAFE
3. Synthetic unstaged changes => UNSAFE
4. Untracked files => WARN (not UNSAFE), exit 1
5. Merge-in-progress detection => UNSAFE
6. Output report structure
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.preflight_check import (
    PreflightIssue,
    PreflightResult,
    check_merge_in_progress,
    check_staged_changes,
    check_untracked_files,
    check_unstaged_changes,
    render_md,
    run_preflight,
)


def _init_git_repo(path: Path) -> None:
    """Create a minimal git repo with one commit."""
    subprocess.run(["git", "init", "-b", "main"], cwd=str(path), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(path), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(path), check=True, capture_output=True)
    (path / "README.md").write_text("# Test\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(path), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=str(path), check=True, capture_output=True)


class TestCleanTree(unittest.TestCase):

    def test_clean_repo_is_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _init_git_repo(repo)
            result = run_preflight(repo)
            self.assertTrue(result.safe_to_run)
            unsafe = [i for i in result.issues if i.level == "UNSAFE"]
            self.assertEqual([], unsafe)

    def test_clean_repo_no_issues(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _init_git_repo(repo)
            result = run_preflight(repo)
            issues = [i for i in result.issues if i.level == "UNSAFE"]
            self.assertEqual([], issues)


class TestStagedChanges(unittest.TestCase):

    def test_staged_changes_returns_unsafe(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _init_git_repo(repo)
            (repo / "new_file.py").write_text("x = 1\n", encoding="utf-8")
            subprocess.run(["git", "add", "new_file.py"], cwd=str(repo), check=True, capture_output=True)
            issue = check_staged_changes(repo)
            self.assertIsNotNone(issue)
            assert issue is not None
            self.assertEqual("UNSAFE", issue.level)
            self.assertIn("staged", issue.message.lower())

    def test_no_staged_changes_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _init_git_repo(repo)
            issue = check_staged_changes(repo)
            self.assertIsNone(issue)


class TestUnstagedChanges(unittest.TestCase):

    def test_unstaged_changes_returns_unsafe(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _init_git_repo(repo)
            (repo / "README.md").write_text("# Modified\n", encoding="utf-8")
            issue = check_unstaged_changes(repo)
            self.assertIsNotNone(issue)
            assert issue is not None
            self.assertEqual("UNSAFE", issue.level)

    def test_no_unstaged_changes_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _init_git_repo(repo)
            issue = check_unstaged_changes(repo)
            self.assertIsNone(issue)


class TestUntrackedFiles(unittest.TestCase):

    def test_untracked_files_returns_warn_not_unsafe(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _init_git_repo(repo)
            (repo / "untracked.txt").write_text("ignored\n", encoding="utf-8")
            issue = check_untracked_files(repo)
            self.assertIsNotNone(issue)
            assert issue is not None
            self.assertEqual("WARN", issue.level)

    def test_untracked_does_not_make_result_unsafe(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _init_git_repo(repo)
            (repo / "untracked.txt").write_text("ignored\n", encoding="utf-8")
            result = run_preflight(repo)
            self.assertTrue(result.safe_to_run)


class TestMergeInProgress(unittest.TestCase):

    def test_merge_head_returns_unsafe(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _init_git_repo(repo)
            # Synthesize a MERGE_HEAD
            (repo / ".git" / "MERGE_HEAD").write_text("abc123\n", encoding="utf-8")
            issue = check_merge_in_progress(repo)
            self.assertIsNotNone(issue)
            assert issue is not None
            self.assertEqual("UNSAFE", issue.level)
            self.assertIn("Merge", issue.message)

    def test_cherry_pick_head_returns_unsafe(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _init_git_repo(repo)
            (repo / ".git" / "CHERRY_PICK_HEAD").write_text("abc123\n", encoding="utf-8")
            issue = check_merge_in_progress(repo)
            self.assertIsNotNone(issue)
            assert issue is not None
            self.assertEqual("UNSAFE", issue.level)

    def test_no_merge_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _init_git_repo(repo)
            issue = check_merge_in_progress(repo)
            self.assertIsNone(issue)


class TestOutputStructure(unittest.TestCase):

    def test_render_md_safe_contains_safe_status(self) -> None:
        result = PreflightResult(safe_to_run=True, issues=[], checks_run=["staged_changes"])
        md = render_md(result)
        self.assertIn("SAFE", md)
        self.assertIn("safe_to_run", md)

    def test_render_md_unsafe_lists_issues(self) -> None:
        result = PreflightResult(
            safe_to_run=False,
            issues=[PreflightIssue("staged_changes", "UNSAFE", "2 staged files.", detail="a.py\nb.py")],
            checks_run=["staged_changes"],
        )
        md = render_md(result)
        self.assertIn("UNSAFE", md)
        self.assertIn("staged_changes", md)

    def test_run_preflight_returns_all_checks_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _init_git_repo(repo)
            result = run_preflight(repo)
            self.assertIn("staged_changes", result.checks_run)
            self.assertIn("unstaged_changes", result.checks_run)
            self.assertIn("untracked_files", result.checks_run)
            self.assertIn("merge_in_progress", result.checks_run)

    def test_output_dir_writes_json_and_md(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _init_git_repo(repo)
            out = Path(tmpdir) / "preflight_out"
            result = subprocess.run(
                [sys.executable, str(Path(__file__).parent.parent / "scripts" / "preflight_check.py"),
                 "--repo", str(repo), "--output-dir", str(out)],
                capture_output=True,
            )
            self.assertTrue((out / "preflight_check.json").exists())
            self.assertTrue((out / "preflight_check.md").exists())
            data = json.loads((out / "preflight_check.json").read_text())
            self.assertIn("safe_to_run", data)
            self.assertIn("issues", data)
            self.assertIn("checks_run", data)


class TestExitCodes(unittest.TestCase):

    def test_clean_repo_exits_0(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _init_git_repo(repo)
            result = subprocess.run(
                [sys.executable, str(Path(__file__).parent.parent / "scripts" / "preflight_check.py"),
                 "--repo", str(repo), "--fail-on-unsafe"],
                capture_output=True,
            )
            self.assertEqual(0, result.returncode)

    def test_staged_changes_with_fail_on_unsafe_exits_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _init_git_repo(repo)
            (repo / "new_file.py").write_text("x = 1\n", encoding="utf-8")
            subprocess.run(["git", "add", "new_file.py"], cwd=str(repo), check=True, capture_output=True)
            result = subprocess.run(
                [sys.executable, str(Path(__file__).parent.parent / "scripts" / "preflight_check.py"),
                 "--repo", str(repo), "--fail-on-unsafe"],
                capture_output=True,
            )
            self.assertEqual(2, result.returncode)


if __name__ == "__main__":
    unittest.main()
