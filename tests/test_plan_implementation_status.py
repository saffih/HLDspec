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


sync = load_module("hld_spec_sync", "hld_spec_sync.py")
import hld_map  # noqa: E402

# HLD-100 has a test that cites it (built); HLD-101 declares a test that does NOT cite it
# (not built yet); HLD-102 is STATUS planned (deferred).
HLD = """# T

## HLD-100 - Built feature

HLD-ID: HLD-100
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: app.py,test_app.py
HLD-VERIFY: built behavior holds

Body for the built feature.

## HLD-101 - Unbuilt feature

HLD-ID: HLD-101
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: app.py,test_app.py
HLD-VERIFY: unbuilt behavior

Body for the not-yet-built feature.

## HLD-102 - Planned feature

HLD-ID: HLD-102
HLD-ROLE: architecture
HLD-STATUS: planned
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD

Future work.
"""

TEST_FILE = "def test_built():  # HLD-100\n    assert True\n"


class PlanImplementationStatusTest(unittest.TestCase):
    def _plan(self):
        tmp = tempfile.mkdtemp()
        ws = Path(tmp) / "proj" / ".hldspec-first-run"
        ws.mkdir(parents=True)
        (Path(tmp) / "proj" / "test_app.py").write_text(TEST_FILE, encoding="utf-8")
        (ws / "HLD.md").write_text(HLD, encoding="utf-8")
        parsed = hld_map.parse_hld_file(ws / "HLD.md")
        plan, _ = sync.build_spec_build_plan(parsed, ws)
        return {str(s["planned_spec_id"]): s for s in plan["planned_specs"]}, parsed, ws

    def test_marks_built_vs_unbuilt_vs_deferred(self):
        by_id, parsed, ws = self._plan()
        # find each spec by its source anchor
        def status_for(anchor):
            for s in by_id.values():
                if anchor in [str(x) for x in s.get("source_hld_sections", [])]:
                    return s.get("implementation_status")
            return None

        self.assertEqual(status_for("HLD-100"), "implemented")
        self.assertEqual(status_for("HLD-101"), "not_built")
        # HLD-102 is STATUS planned -> deferred (it may not even be a planned spec; if it
        # is, it must be marked deferred, never implemented).
        s102 = status_for("HLD-102")
        self.assertIn(s102, (None, "deferred"))

    def test_built_spec_is_marked_not_dropped(self):
        # Mark, don't exclude: the built anchor's spec MUST still be present in the plan.
        by_id, _, _ = self._plan()
        present = any(
            "HLD-100" in [str(x) for x in s.get("source_hld_sections", [])]
            for s in by_id.values()
        )
        self.assertTrue(present, "built anchor's spec was dropped from the plan; it must be marked, not excluded")

    def test_status_helper_reads_hld_structure(self):
        # The helper keys off HLD-STATUS and HLD-RESOURCES (structured fields), not guesses.
        tmp = tempfile.mkdtemp()
        ws = Path(tmp) / "p" / ".hldspec-first-run"
        ws.mkdir(parents=True)
        (Path(tmp) / "p" / "test_app.py").write_text(TEST_FILE, encoding="utf-8")
        (ws / "HLD.md").write_text(HLD, encoding="utf-8")
        parsed = hld_map.parse_hld_file(ws / "HLD.md")
        by_id = parsed.section_by_id()
        self.assertEqual(sync.anchor_implementation_status(by_id["HLD-100"], ws), "implemented")
        self.assertEqual(sync.anchor_implementation_status(by_id["HLD-101"], ws), "not_built")
        self.assertEqual(sync.anchor_implementation_status(by_id["HLD-102"], ws), "deferred")


if __name__ == "__main__":
    unittest.main()
