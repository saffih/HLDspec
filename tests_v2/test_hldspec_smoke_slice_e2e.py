from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import hldspec_smoke_slice_e2e as smoke  # noqa: E402

SCRIPT = ROOT / "scripts" / "hldspec_smoke_slice_e2e.py"
BAD_HLD = ROOT / "tests_v2" / "fixtures" / "bad_smoke_HLD_missing_anchor.md"


class SmokeE2eDirectTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-smoke-test-")
        self.temp_root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_smoke_passes(self) -> None:
        result = smoke.run_smoke(self.temp_root)
        self.assertTrue(result.passed, result.failures)

    def test_source_hld_and_target_paths_match_contract(self) -> None:
        result = smoke.run_smoke(self.temp_root)
        self.assertEqual(self.temp_root / "tiny_HLD.md", result.source_hld)
        self.assertEqual(self.temp_root / "target", result.target)
        self.assertTrue(result.source_hld.is_file())
        self.assertTrue(result.target.is_dir())

    def test_all_expected_artifacts_exist_under_target(self) -> None:
        result = smoke.run_smoke(self.temp_root)
        self.assertTrue(result.passed, result.failures)
        expected = smoke._load_expected_artifacts()
        for rel in expected:
            self.assertTrue((result.target / rel).is_file(), rel)
            self.assertIn(rel, result.artifacts)

    def test_no_generated_artifacts_escape_target_except_source_hld(self) -> None:
        result = smoke.run_smoke(self.temp_root)
        self.assertTrue(result.passed, result.failures)
        self.assertEqual({"tiny_HLD.md", "target"}, {path.name for path in self.temp_root.iterdir()})

    def test_required_source_package_and_mirror_dirs_created(self) -> None:
        result = smoke.run_smoke(self.temp_root)
        self.assertTrue((result.target / ".hldspec" / "source_package").is_dir())
        self.assertTrue((result.target / ".specify" / "source").is_dir())

    def test_reference_map_contains_all_anchors(self) -> None:
        result = smoke.run_smoke(self.temp_root)
        ref_map = json.loads(
            (result.target / ".hldspec/source_package/hld_reference_map.json")
            .read_text(encoding="utf-8")
        )
        present = set(ref_map["anchors"].keys())
        for anchor in smoke.SMOKE_ANCHORS:
            self.assertIn(anchor, present)

    def test_single_spec_input_cites_all_anchors(self) -> None:
        result = smoke.run_smoke(self.temp_root)
        text = (
            result.target / ".hldspec/source_package/speckit_single_spec_input.md"
        ).read_text(encoding="utf-8")
        for anchor in smoke.SMOKE_ANCHORS:
            self.assertIn(f"({anchor})", text)

    def test_slice_policy_is_validated_when_present(self) -> None:
        result = smoke.run_smoke(self.temp_root)
        self.assertTrue(result.passed, result.failures)
        self.assertTrue((result.target / ".hldspec/source_package/implementation_slices.json").is_file())
        self.assertTrue(
            (result.target / ".hldspec/source_package/implementation_slicing_policy.md").is_file()
            or (result.target / ".hldspec/source_package/slice_execution_policy.md").is_file()
        )

    def test_bad_hld_missing_anchor_fails(self) -> None:
        result = smoke.run_smoke(self.temp_root, hld_fixture=BAD_HLD)
        self.assertFalse(result.passed)
        self.assertTrue(
            any("HLD-003" in failure for failure in result.failures),
            result.failures,
        )

    def test_smoke_is_idempotent(self) -> None:
        first = smoke.run_smoke(self.temp_root)
        second = smoke.run_smoke(self.temp_root)
        self.assertTrue(first.passed, first.failures)
        self.assertTrue(second.passed, second.failures)


class SmokeE2eSubprocessTests(unittest.TestCase):
    def _run(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *extra],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_script_exits_zero_and_stdout_is_pass_line(self) -> None:
        result = self._run()
        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        self.assertEqual("HLDSPEC_SMOKE_RESULT: PASS\n", result.stdout)

    def test_failure_stdout_is_fail_line(self) -> None:
        result = self._run("--hld", str(BAD_HLD))
        self.assertEqual(1, result.returncode)
        self.assertEqual("HLDSPEC_SMOKE_RESULT: FAIL\n", result.stdout)
        self.assertIn("HLD-003", result.stderr)

    def test_json_mode_emits_summary_then_final_result_line(self) -> None:
        result = self._run("--json")
        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        self.assertEqual("HLDSPEC_SMOKE_RESULT: PASS", lines[-1])
        payload = json.loads("\n".join(lines[:-1]))
        self.assertEqual("PASS", payload["result"])
        self.assertTrue(payload["target"].endswith("/target"))
        self.assertTrue(payload["source_hld"].endswith("/tiny_HLD.md"))

    def test_keep_flag_preserves_temp_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hldspec-smoke-") as tmp:
            result = self._run("--root", tmp, "--keep")
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            self.assertTrue((Path(tmp) / "tiny_HLD.md").is_file())
            self.assertTrue((Path(tmp) / "target" / ".hldspec" / "source_package" / "HLD.md").is_file())

    def test_without_keep_removes_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hldspec-smoke-parent-") as parent:
            root = Path(parent) / "hldspec-smoke-delete-me"
            result = self._run("--root", str(root))
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()
