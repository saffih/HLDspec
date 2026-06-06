from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_module(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {rel}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fresh = load_module("check_workspace_freshness", "scripts/check_workspace_freshness.py")

CONVERTED_HLD = "# T\n\n## HLD-001 - X\n\nHLD-ID: HLD-001\nHLD-ROLE: purpose\n\nbody\n"


class FreshnessHelperTest(unittest.TestCase):
    def test_absent_then_fresh_then_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            ws.mkdir()
            hld = Path(tmp) / "HLD.md"
            hld.write_text("v1", encoding="utf-8")
            self.assertEqual(fresh.status(ws, hld), "absent")
            fresh.record(ws, hld)
            self.assertEqual(fresh.status(ws, hld), "fresh")
            hld.write_text("v2 changed", encoding="utf-8")
            self.assertEqual(fresh.status(ws, hld), "stale")

    def test_legacy_stale_warning_names_actual_working_hld_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / ".hldspec-first-run"
            ws.mkdir()
            working = ws / "HLD.md"
            working.write_text("workspace copy\n", encoding="utf-8")
            source = Path(tmp) / "HLD.md"
            source.write_text("source truth\n", encoding="utf-8")

            fresh.record(ws, source)
            report = json.loads((ws / ".hldspec" / "source_freshness.json").read_text(encoding="utf-8"))

            warning_text = "\n".join(report["warnings"])
            self.assertIn(str(working.resolve()), warning_text)
            self.assertNotIn("targetHLD/HLD.md", warning_text)


class FreshnessGateShellTest(unittest.TestCase):
    """The gate must fire through the real shell entry point, not just the helper."""

    def _run(self, source: Path, workspace: Path, env_extra=None):
        env = dict(os.environ)
        env["HLDSPEC_SKIP_PREFLIGHT"] = "1"
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            ["bash", str(ROOT / "scripts" / "project_continue.sh"), str(source), str(workspace)],
            cwd=ROOT, env=env, capture_output=True, text=True,
        )

    def test_stale_workspace_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / ".hldspec-first-run"
            (ws / "firstrun" / ".specify" / "sync").mkdir(parents=True)
            (ws / "HLD.md").write_text(CONVERTED_HLD, encoding="utf-8")
            (ws / "firstrun" / ".specify" / "sync" / "spec_build_plan_review.md").write_text("review", encoding="utf-8")
            source = Path(tmp) / "HLD.md"
            source.write_text("source v1\n", encoding="utf-8")
            fresh.record(ws, source)              # workspace built from v1
            source.write_text("source v2 — changed\n", encoding="utf-8")  # source now differs

            res = self._run(source, ws)
            self.assertEqual(res.returncode, 3, res.stderr)
            self.assertIn("STALE WORKSPACE", res.stderr)

    def test_unverifiable_built_workspace_is_refused(self) -> None:
        # No fingerprint + an already-built workspace must NOT be silently adopted.
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / ".hldspec-first-run"
            (ws / "firstrun" / ".specify" / "sync").mkdir(parents=True)
            (ws / "HLD.md").write_text(CONVERTED_HLD, encoding="utf-8")
            (ws / "firstrun" / ".specify" / "sync" / "spec_build_plan_review.md").write_text("review", encoding="utf-8")
            source = Path(tmp) / "HLD.md"
            source.write_text("source\n", encoding="utf-8")

            res = self._run(source, ws)
            self.assertEqual(res.returncode, 3, res.stderr)
            self.assertIn("STALE WORKSPACE", res.stderr)

    def test_legacy_freshness_record_does_not_force_new_layout_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / ".hldspec-first-run"
            ws.mkdir()
            (ws / "HLD.md").write_text(CONVERTED_HLD, encoding="utf-8")
            source = Path(tmp) / "HLD.md"
            source.write_text(CONVERTED_HLD, encoding="utf-8")
            fresh.record(ws, source)

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_hldspec_state.py"),
                    str(ws),
                    "--source-hld",
                    str(source),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            self.assertTrue((ws / ".specify" / "sync" / "hldspec_state.json").exists())
            self.assertFalse((ws / ".hldspec" / "sync" / "hldspec_state.json").exists())
            self.assertNotIn("NO_WORKSPACE", result.stdout)

    def test_fresh_rebuild_refuses_unsafe_workspace_name(self) -> None:
        # HLDSPEC_FRESH wipe must refuse a workspace whose basename is not .hldspec*.
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "not-an-hldspec-dir"
            ws.mkdir()
            (ws / "HLD.md").write_text(CONVERTED_HLD, encoding="utf-8")
            source = Path(tmp) / "HLD.md"
            source.write_text("source\n", encoding="utf-8")

            res = self._run(source, ws, env_extra={"HLDSPEC_FRESH": "1"})
            self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
            self.assertIn("refusing to wipe", res.stderr)


if __name__ == "__main__":
    unittest.main()
