from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RunSkepticFileNamingTests(unittest.TestCase):
    def test_skeptic_cache_uses_snake_case_files_and_runskeptic_trigger(self) -> None:
        cache_path = ROOT / "docs" / "skeptic_framework_cache.json"
        self.assertTrue(cache_path.exists())
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        self.assertEqual("RunSkeptic", cache["formal_invocation"])
        self.assertEqual("saffih/skeptic", cache["authoritative_source"]["repository"])
        self.assertEqual("skeptic.md", cache["authoritative_source"]["path"])
        self.assertIn("INFERRED_RISK", cache["evidence_levels"])

    def test_writer_copies_skeptic_cache_to_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "write_skeptic_cache.py"), td],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(0, result.returncode, msg=result.stderr)
            workspace_cache = Path(td) / ".specify" / "sync" / "skeptic_framework_cache.json"
            self.assertTrue(workspace_cache.exists())

    def test_no_camel_case_cache_paths_in_tests_or_scripts(self) -> None:
        bad = []
        for rel in ["tests", "scripts"]:
            for path in (ROOT / rel).rglob("*"):
                if not path.is_file() or path.suffix not in {".py", ".sh"}:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                forbidden_cache = "RUN" + "SKEPTIC_FRAMEWORK_CACHE"
                forbidden_writer = "write_" + "RunSkeptic" + "_cache.py"
                if forbidden_cache in text or forbidden_writer in text:
                    bad.append(str(path.relative_to(ROOT)))
        self.assertEqual([], bad)


if __name__ == "__main__":
    unittest.main()
