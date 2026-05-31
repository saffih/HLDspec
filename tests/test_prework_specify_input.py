from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
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


prework = load_module("build_speckit_prework_plan", "scripts/build_speckit_prework_plan.py")

HLD = """# T

## HLD-014 - Orphaned-work recovery (lease, reclaim, fence)

HLD-ID: HLD-014
HLD-ROLE: architecture
HLD-VERIFY: a silent session's task is reclaimed to pending; done/escalate/split by a stale owner are rejected

A session can claim a task and then vanish. Reclaim returns it to pending and clears
the assignee; note/decide/reply stay multi-writer.
"""

SPEC = {
    "planned_spec_id": "014",
    "title": "Orphaned-work recovery (lease, reclaim, fence)",
    "source_hld_sections": ["HLD-014"],
    "product_context": {
        "acceptance_criteria": ["A silent session's task is reclaimed or escalated."],
    },
    "architecture_context": {
        "contracts": [{"contract_name": "Orphaned-work recovery (lease, reclaim, fence) Contract"}],
    },
}


class PreworkSpecifyInputTest(unittest.TestCase):
    def test_specify_input_carries_hld_prose_and_facts(self):
        # The first touch point (specify) must hand SpecKit everything we already know:
        # the anchor's own HLD prose + the extracted acceptance criteria and contracts —
        # not just "Build X. Source HLD sections: Y".
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            (ws / ".specify" / "sync").mkdir(parents=True)
            (ws / "HLD.md").write_text(HLD, encoding="utf-8")
            plan_path = ws / ".specify" / "sync" / "spec_build_plan.json"
            plan_path.write_text("{}", encoding="utf-8")  # only its path matters here

            hld_sections = prework.load_hld_section_text(plan_path)
            self.assertIn("HLD-014", hld_sections)

            item = prework.build_feature_item(SPEC, 1, hld_sections)
            si = item["speckit_specify_input"]

            # HLD prose (the authoritative WHAT, incl. the HLD-VERIFY line) is injected.
            self.assertIn("HLD-VERIFY", si)
            self.assertIn("clears", si)
            self.assertIn("multi-writer", si)
            # Extracted product + contract facts are injected.
            self.assertIn("reclaimed or escalated", si)
            self.assertIn("Orphaned-work recovery (lease, reclaim, fence) Contract", si)
            # And it is substantially richer than the old 3-line stub.
            self.assertGreater(len(si.splitlines()), 8)

    def test_missing_hld_falls_back_without_crashing(self):
        # A raw/unanchored run with no working HLD must not crash; minimal input stands.
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            (ws / ".specify" / "sync").mkdir(parents=True)
            plan_path = ws / ".specify" / "sync" / "spec_build_plan.json"
            plan_path.write_text("{}", encoding="utf-8")
            self.assertEqual(prework.load_hld_section_text(plan_path), {})
            item = prework.build_feature_item(SPEC, 1, {})
            self.assertIn("Build Orphaned-work recovery", item["speckit_specify_input"])


if __name__ == "__main__":
    unittest.main()
