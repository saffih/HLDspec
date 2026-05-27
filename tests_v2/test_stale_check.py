import tempfile
import unittest
from pathlib import Path

from hldspec import gate_validator as gv
from hldspec import hld_marking as hm
from hldspec import hld_source_package as sp
from hldspec import session_control as sc
from hldspec import stale_check as st
from hldspec.workspace_adapter import TargetWorkspaceAdapter

BASE = """# HLD

## HLD-001 - Purpose

HLD-ID: HLD-001
HLD-ROLE: purpose
HLD-STATUS: active
HLD-RISK: LOW

### Purpose
Alpha behavior.

## HLD-002 - Engine

HLD-ID: HLD-002
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: LOW

### Purpose
Beta behavior.
"""


def _ref(text):
    return hm.build_reference_map(text)


class ClassificationTests(unittest.TestCase):
    def test_changed_cited_anchor_is_regenerate_and_stale(self):
        old = _ref(BASE)
        new = _ref(BASE.replace("Beta behavior.", "Beta behavior changed."))
        impact = st.build_change_impact(old, new, derived_citations={"HLD-002": ["speckit_single_spec_input.md"]})
        self.assertEqual(impact["overall"], st.REGENERATE)
        change = next(c for c in impact["changes"] if c["anchor"] == "HLD-002")
        self.assertEqual(change["classification"], st.REGENERATE)
        self.assertIn("HLD-002", impact["stale_anchors"])
        self.assertIn("speckit_single_spec_input.md", change["cited_by"])

    def test_deleted_cited_anchor_blocks(self):
        old = _ref(BASE)
        new = _ref(BASE.split("## HLD-002")[0])
        impact = st.build_change_impact(old, new, derived_citations={"HLD-002": ["speckit_single_spec_input.md"]})
        self.assertEqual(impact["overall"], st.BLOCK)
        self.assertIn("HLD-002", impact["stale_anchors"])
        self.assertTrue(any(c["classification"] == st.BLOCK for c in impact["blocking"]))

    def test_added_anchor_is_review_not_stale(self):
        old = _ref(BASE.split("## HLD-002")[0])
        new = _ref(BASE)
        impact = st.build_change_impact(old, new, derived_citations={})
        change = next(c for c in impact["changes"] if c["anchor"] == "HLD-002")
        self.assertEqual(change["kind"], "added")
        self.assertEqual(change["classification"], st.REVIEW)
        self.assertNotIn("HLD-002", impact["stale_anchors"])

    def test_moved_anchor_does_not_require_regeneration(self):
        old = _ref(BASE)
        new = _ref(BASE.replace("## HLD-002 - Engine", "\n## HLD-002 - Engine"))
        impact = st.build_change_impact(old, new, derived_citations={"HLD-002": ["speckit_single_spec_input.md"]})
        change = next(c for c in impact["changes"] if c["anchor"] == "HLD-002")
        self.assertEqual(change["kind"], "moved")
        self.assertEqual(change["classification"], st.REVIEW)
        self.assertNotIn("HLD-002", impact["stale_anchors"])

    def test_unknown_citation_blocks(self):
        old = _ref(BASE)
        new = _ref(BASE)
        impact = st.build_change_impact(old, new, derived_citations={"HLD-999": ["speckit_single_spec_input.md"]})
        self.assertEqual(impact["overall"], st.BLOCK)
        self.assertIn("HLD-999", impact["stale_anchors"])

    def test_formatting_change_uncited_is_review_not_safe(self):
        # Hash flips on any text change; an uncited whitespace edit is REVIEW, never SAFE.
        old = _ref(BASE)
        new = _ref(BASE.replace("Beta behavior.", "Beta behavior. "))
        impact = st.build_change_impact(old, new, derived_citations={})
        change = next(c for c in impact["changes"] if c["anchor"] == "HLD-002")
        self.assertEqual(change["classification"], st.REVIEW)
        self.assertNotEqual(impact["overall"], st.SAFE)

    def test_no_change_is_safe(self):
        impact = st.build_change_impact(_ref(BASE), _ref(BASE), derived_citations={})
        self.assertEqual(impact["overall"], st.SAFE)
        self.assertEqual(impact["stale_anchors"], [])


class ReportTests(unittest.TestCase):
    def test_report_lists_affected_files_and_anchors(self):
        old = _ref(BASE)
        new = _ref(BASE.replace("Beta behavior.", "Beta behavior changed."))
        impact = st.build_change_impact(old, new, derived_citations={"HLD-002": ["speckit_single_spec_input.md"]})
        report = st.render_stale_report(impact)
        self.assertIn("HLD-002", report)
        self.assertIn("speckit_single_spec_input.md", report)
        self.assertIn("Stale Artifact Report", report)


class GateIntegrationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.target = Path(self._tmp.name)
        self.adapter = TargetWorkspaceAdapter(target_root=self.target, layout="new")
        self.source_dir = self.adapter.source_package_dir
        # Build a real source package from BASE so reference_map + single spec exist.
        sp.build_source_package_content(self.target, BASE, hld_source_ref="/src/HLD.md")

    def tearDown(self):
        self._tmp.cleanup()

    def test_run_stale_check_writes_artifacts(self):
        changed = BASE.replace("Beta behavior.", "Beta behavior changed.")
        impact = st.run_stale_check(self.target, changed)
        self.assertTrue((self.source_dir / st.CHANGE_IMPACT_FILE).is_file())
        self.assertTrue((self.source_dir / st.STALE_REPORT_FILE).is_file())
        # HLD-002 is cited by the generated single-spec input -> stale.
        self.assertIn("HLD-002", impact["stale_anchors"])

    def test_gate_validator_blocks_stale_cited_anchors(self):
        st.run_stale_check(self.target, BASE.replace("Beta behavior.", "Beta behavior changed."))
        stale = st.load_stale_anchors(self.source_dir)
        self.assertIn("HLD-002", stale)
        ctx = gv.GateContext(
            receipt_present=True, source_refs=["HLD-001"],
            runskeptic_status=gv.RUNSKEPTIC_PASS, consultant_status=gv.CONSULTANT_PASS,
            human_approved=True, stale_anchors=stale,
        )
        result = gv.validate_gate(gv.SOURCE_PACKAGE_APPROVAL_GATE, ctx)
        self.assertFalse(result.passed)
        self.assertTrue(any("stale anchors" in b for b in result.blockers))

    def test_preflight_merges_impact_stale_anchors(self):
        # Build a passing session + phase report, then introduce stale impact.
        plan = sc.build_session_plan(self.target, Path.cwd())
        plan["approvals"] = {gv.SOURCE_PACKAGE_APPROVAL_GATE: True}
        sc.write_session_artifacts(self.target, plan)
        # write_session_artifacts overwrites session_plan.json without approvals; re-write.
        from hldspec.script_io import write_json_dict
        write_json_dict(self.source_dir / sc.SESSION_PLAN_FILE, plan)
        write_json_dict(self.source_dir / sc.PHASE_REPORT_FILE, {
            "phase": "p", "actor": sc.RUNNER, "validation_result": "PASS",
            "runskeptic_result": gv.RUNSKEPTIC_PASS, "consultant_result": gv.CONSULTANT_PASS,
            "source_anchors_used": ["HLD-001"], "next_safe_action": "go",
        })
        write_json_dict(self.source_dir / sc.CONTEXT_RECEIPT_FILE, {
            "required_files_read": sc.REQUIRED_READS, "current_phase": "p", "actor": sc.RUNNER,
            "model_tier": "MODEL_SIMPLE", "stop_condition": "stop", "validation_command": "x",
        })
        # Without stale impact -> allowed.
        ok = sc.session_continue_preflight(self.target, check_dirty=False)
        self.assertTrue(ok.allowed, msg=ok.blockers)
        # Introduce stale impact -> blocked.
        st.run_stale_check(self.target, BASE.replace("Beta behavior.", "Beta behavior changed."))
        blocked = sc.session_continue_preflight(self.target, check_dirty=False)
        self.assertFalse(blocked.allowed)
        self.assertTrue(any("stale anchors" in b for b in blocked.blockers))


if __name__ == "__main__":
    unittest.main()
