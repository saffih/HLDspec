import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "hldspec_smoke_slice_e2e.py"
FIXTURES = ROOT / "tests_v2" / "fixtures"


class HldspecSmokeSliceE2ETests(unittest.TestCase):
    def run_smoke(self, *args, env=None):
        merged_env = os.environ.copy()
        merged_env["PYTHONDONTWRITEBYTECODE"] = "1"
        merged_env["PYTHONPYCACHEPREFIX"] = str(ROOT / ".tmp" / "pycache")
        if env:
            merged_env.update(env)
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=str(ROOT),
            env=merged_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

    def parse_json_line(self, output: str) -> dict:
        for line in output.splitlines():
            if line.startswith("HLDSPEC_SMOKE_JSON: "):
                return json.loads(line.split(": ", 1)[1])
        self.fail(f"missing JSON line in output:\n{output}")

    def test_pass_path_with_temp_target(self):
        root = Path(tempfile.mkdtemp(prefix="hldspec-smoke-test-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        cp = self.run_smoke("--target-root", str(root), "--keep", "--json")
        self.assertEqual(cp.returncode, 0, cp.stdout)
        self.assertIn("HLDSPEC_SMOKE_RESULT: PASS", cp.stdout)
        data = self.parse_json_line(cp.stdout)
        self.assertEqual(data["result"], "PASS")
        self.assertEqual(data["target_dir"], str(root / "target"))
        for rel in (FIXTURES / "expected_smoke_artifacts.txt").read_text(encoding="utf-8").splitlines():
            self.assertTrue((root / "target" / rel).exists(), rel)

    def test_fail_path_with_negative_hld(self):
        root = Path(tempfile.mkdtemp(prefix="hldspec-smoke-test-bad-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        cp = self.run_smoke(
            "--target-root", str(root),
            "--source-hld", str(FIXTURES / "bad_smoke_HLD_missing_anchor.md"),
            "--json",
        )
        self.assertNotEqual(cp.returncode, 0, cp.stdout)
        self.assertIn("HLDSPEC_SMOKE_RESULT: FAIL", cp.stdout)
        data = self.parse_json_line(cp.stdout)
        self.assertEqual(data["result"], "FAIL")
        self.assertTrue(data["preserved"])
        self.assertIn("HLD-002", data["failed_check"] or "")

    def test_keep_preserves_output(self):
        root = Path(tempfile.mkdtemp(prefix="hldspec-smoke-test-keep-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        cp = self.run_smoke("--target-root", str(root), "--keep")
        self.assertEqual(cp.returncode, 0, cp.stdout)
        self.assertTrue((root / "target" / ".hldspec" / "source_package").is_dir())

    def test_json_output_contract(self):
        root = Path(tempfile.mkdtemp(prefix="hldspec-smoke-test-json-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        cp = self.run_smoke("--target-root", str(root), "--keep", "--json")
        self.assertEqual(cp.returncode, 0, cp.stdout)
        data = self.parse_json_line(cp.stdout)
        for key in ("result", "source_hld", "target_dir", "checks", "failed_check", "tmux_status", "preserved"):
            self.assertIn(key, data)

    def test_tmux_missing_path_skips_not_fails(self):
        root = Path(tempfile.mkdtemp(prefix="hldspec-smoke-test-tmux-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        cp = self.run_smoke(
            "--target-root", str(root), "--keep", "--json", "--tmux",
            env={"HLDSPEC_SMOKE_FORCE_NO_TMUX": "1"},
        )
        self.assertEqual(cp.returncode, 0, cp.stdout)
        data = self.parse_json_line(cp.stdout)
        self.assertEqual(data["tmux_status"], "SKIP_TMUX")
        self.assertIn("HLDSPEC_SMOKE_RESULT: PASS", cp.stdout)

    def test_no_repo_pollution_assertion(self):
        root = Path(tempfile.mkdtemp(prefix="hldspec-smoke-test-clean-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        cp = self.run_smoke("--target-root", str(root), "--keep", "--json")
        self.assertEqual(cp.returncode, 0, cp.stdout)
        data = self.parse_json_line(cp.stdout)
        self.assertFalse(data["repo_status_changed"])


if __name__ == "__main__":
    unittest.main()
