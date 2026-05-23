from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_module(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


arch = load_module("build_hldspec_architecture_analysis", "scripts/build_hldspec_architecture_analysis.py")
constitution = load_module("build_speckit_constitution_context", "scripts/build_speckit_constitution_context.py")
speclist = load_module("build_hldspec_speckit_spec_list", "scripts/build_hldspec_speckit_spec_list.py")
readiness = load_module("run_hldspec_speckit_readiness", "scripts/run_hldspec_speckit_readiness.py")


SAMPLE_HLD = """# Sample HLD

## HLD-010 - Database API Interface
HLD-ID: HLD-010
HLD-ROLE: architecture
HLD-STATUS: draft
HLD-RISK: medium
HLD-SPECS: TBD
HLD-RESOURCES: database
HLD-VERIFY: review

This section defines database persistence, data state ownership, programmatic interface, and API contract behavior.

## HLD-020 - Processing Core
HLD-ID: HLD-020
HLD-ROLE: architecture
HLD-STATUS: draft
HLD-RISK: medium
HLD-SPECS: TBD
HLD-RESOURCES: processing
HLD-VERIFY: review

This section defines orchestration logic and lifecycle processing.
"""


class HldspecSpeckitReadyTest(unittest.TestCase):
    def make_workspace(self) -> tuple[Path, tempfile.TemporaryDirectory]:
        tmp = tempfile.TemporaryDirectory()
        workspace = Path(tmp.name) / "workspace"
        workspace.mkdir()
        (workspace / "HLD.md").write_text(SAMPLE_HLD, encoding="utf-8")
        (workspace / ".specify" / "sync").mkdir(parents=True)
        return workspace, tmp

    def test_architecture_analysis_detects_layered_boundary(self) -> None:
        workspace, tmp = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        data = arch.build_analysis(workspace)

        self.assertEqual(data["section_count"], 2)
        self.assertTrue(any(f["hld_id"] == "HLD-010" for f in data["findings"]))
        hld010 = next(s for s in data["sections"] if s["hld_id"] == "HLD-010")
        self.assertTrue(hld010["requires_layered_split"])

    def test_constitution_context_has_required_shared_context(self) -> None:
        workspace, tmp = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        data = arch.build_analysis(workspace)
        sync = workspace / ".specify" / "sync"
        (sync / "hldspec_architecture_analysis.json").write_text(json.dumps(data), encoding="utf-8")

        context = constitution.build_context(workspace)

        self.assertIn("architecture_layer_model", context)
        self.assertIn("interface_taxonomy", context)
        self.assertIn("split_rules", context)
        self.assertIn("no_invention_rules", context)
        self.assertIn("checkpoint_triage_rules", context)

    def test_spec_list_splits_mixed_database_api_section(self) -> None:
        workspace, tmp = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        data = arch.build_analysis(workspace)
        sync = workspace / ".specify" / "sync"
        (sync / "hldspec_architecture_analysis.json").write_text(json.dumps(data), encoding="utf-8")

        result = speclist.build_list(workspace)
        titles = "\n".join(str(s["title"]) for s in result["specs"])

        self.assertIn("Database API Interface - Database Tool Interface", titles)
        self.assertIn("Database API Interface - Use Logic and Orchestration", titles)
        self.assertIn("Database API Interface - API Contract", titles)
        self.assertEqual(result["status"], "SPEC_LIST_READY_FOR_REVIEW")

    def test_wrapper_generates_readiness_artifacts(self) -> None:
        workspace, tmp = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        subprocess.run(
            ["bash", str(ROOT / "scripts" / "hldspec_speckit_ready.sh"), str(workspace)],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        sync = workspace / ".specify" / "sync"
        self.assertTrue((sync / "hldspec_architecture_analysis.json").exists())
        self.assertTrue((sync / "speckit_constitution_context.json").exists())
        self.assertTrue((sync / "hldspec_speckit_spec_list.json").exists())
        self.assertTrue((sync / "hldspec_speckit_readiness.json").exists())

        review = readiness.build_review(workspace)
        self.assertEqual(review["status"], "SPECKIT_PREWORK_READY_FOR_HUMAN_REVIEW")
        self.assertFalse(review["implementation_allowed"])
        self.assertTrue(review["not_real_speckit_execution"])


if __name__ == "__main__":
    unittest.main()
