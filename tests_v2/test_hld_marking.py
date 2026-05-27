import tempfile
import unittest
from pathlib import Path

from hldspec import hld_marking as hm
from hldspec import hld_source_package as sp
from hldspec import single_spec_input as ssi

HLD = """# HLD

## HLD-001 - Purpose

HLD-ID: HLD-001
HLD-ROLE: purpose
HLD-STATUS: active
HLD-RISK: LOW

### Purpose
The system syncs HLDs into SpecKit packages.

## HLD-002 - Sync Engine

HLD-ID: HLD-002
HLD-ROLE: processing
HLD-STATUS: needs-review
HLD-RISK: HIGH

### Purpose
Sync engine. TBD: decide retry policy.
"""

DUP_HLD = """# HLD

## HLD-001 - One

HLD-ID: HLD-001
HLD-ROLE: purpose
HLD-STATUS: active
HLD-RISK: LOW

## HLD-001 - Again

HLD-ID: HLD-001
HLD-ROLE: purpose
HLD-STATUS: active
HLD-RISK: LOW
"""


class ReferenceMapTests(unittest.TestCase):
    def test_reference_map_has_anchor_heading_hash(self):
        ref = hm.build_reference_map(HLD)
        self.assertIn("HLD-001", ref["anchors"])
        entry = ref["anchors"]["HLD-001"]
        self.assertEqual(entry["heading"], "## HLD-001 - Purpose")
        self.assertEqual(entry["title"], "Purpose")
        self.assertEqual(len(entry["sha256"]), 64)
        self.assertEqual(entry["role"], "purpose")

    def test_hash_changes_with_content(self):
        a = hm.build_reference_map(HLD)["anchors"]["HLD-002"]["sha256"]
        b = hm.build_reference_map(HLD.replace("retry policy", "backoff policy"))["anchors"]["HLD-002"]["sha256"]
        self.assertNotEqual(a, b)

    def test_anchor_ids(self):
        self.assertEqual(hm.anchor_ids(HLD), {"HLD-001", "HLD-002"})


class MarkingTests(unittest.TestCase):
    def test_marked_hld_contains_every_anchor(self):
        marked = hm.build_marked_hld(HLD)
        self.assertIn("<!-- ANCHOR: HLD-001 -->", marked)
        self.assertIn("<!-- ANCHOR: HLD-002 -->", marked)

    def test_marked_hld_preserves_original_lines(self):
        marked = hm.build_marked_hld(HLD)
        self.assertIn("The system syncs HLDs into SpecKit packages.", marked)

    def test_duplicate_anchors_rejected(self):
        self.assertIn("HLD-001", hm.duplicate_anchors(DUP_HLD))
        self.assertTrue(any("duplicate" in e.lower() for e in hm.validate_marking(DUP_HLD)))

    def test_clean_hld_has_no_duplicates(self):
        self.assertEqual([], hm.duplicate_anchors(HLD))


class SingleSpecInputTests(unittest.TestCase):
    def test_single_input_cites_anchors(self):
        text = ssi.build_single_spec_input(HLD)
        self.assertIn("- (HLD-001)", text)
        self.assertIn("- (HLD-002)", text)

    def test_no_unsupported_claims_in_generated_input(self):
        text = ssi.build_single_spec_input(HLD)
        self.assertEqual([], ssi.find_unsupported_claims(text, hm.anchor_ids(HLD)))

    def test_open_questions_preserved(self):
        text = ssi.build_single_spec_input(HLD)
        self.assertIn("## Open Questions", text)
        self.assertIn("needs-review", text)
        self.assertIn("TBD", text)

    def test_single_input_is_one_document(self):
        # Exactly one Requirements section -> one spec input, not many specs.
        text = ssi.build_single_spec_input(HLD)
        self.assertEqual(text.count("## Requirements"), 1)

    def test_unsupported_claim_missing_prefix_flagged(self):
        bad = "## Requirements\n\n- a claim with no anchor citation\n"
        flagged = ssi.find_unsupported_claims(bad, {"HLD-001"})
        self.assertEqual(len(flagged), 1)
        self.assertIn("missing (HLD-NNN) prefix", flagged[0])

    def test_unsupported_claim_unknown_anchor_flagged(self):
        bad = "## Requirements\n\n- (HLD-999) cites a non-existent anchor\n"
        flagged = ssi.find_unsupported_claims(bad, {"HLD-001"})
        self.assertEqual(len(flagged), 1)
        self.assertIn("unknown anchor", flagged[0])

    def test_bullets_outside_requirements_not_flagged(self):
        text = "## Source HLD Anchors\n\n- HLD-001: Purpose\n\n## Open Questions\n\n- (none)\n"
        self.assertEqual([], ssi.find_unsupported_claims(text, {"HLD-001"}))


class ContentFlowTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.target = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_build_produces_valid_non_empty_package(self):
        build = sp.build_source_package_content(self.target, HLD, hld_source_ref="/src/HLD.md")
        self.assertTrue(build.ok, msg=f"{build.validation.missing} {build.unsupported_claims}")
        self.assertEqual(build.anchor_count, 2)
        self.assertEqual(build.unsupported_claims, [])
        self.assertTrue((build.source_dir / "speckit_single_spec_input.md").is_file())
        self.assertTrue((build.source_dir / "hld_reference_map.json").is_file())

    def test_mirror_marked_hld_has_generated_banner(self):
        sp.build_source_package_content(self.target, HLD, hld_source_ref="/src/HLD.md")
        mirror = self.target / ".specify" / "source" / "HLD.marked.md"
        self.assertTrue(mirror.is_file())
        self.assertIn("GENERATED by HLDspec", mirror.read_text(encoding="utf-8"))

    def test_authoritative_single_spec_has_no_mirror_banner(self):
        build = sp.build_source_package_content(self.target, HLD, hld_source_ref="/src/HLD.md")
        text = (build.source_dir / "speckit_single_spec_input.md").read_text(encoding="utf-8")
        self.assertNotIn("derived read-only mirror", text)

    def test_duplicate_anchor_hld_fails_build(self):
        build = sp.build_source_package_content(self.target, DUP_HLD, hld_source_ref="/src/HLD.md")
        self.assertFalse(build.ok)
        self.assertTrue(any("duplicate" in e.lower() for e in build.marking_errors))

    def test_empty_hld_still_builds_valid_container(self):
        build = sp.build_source_package_content(self.target, "# HLD\n", hld_source_ref="/src/HLD.md")
        self.assertEqual(build.anchor_count, 0)
        self.assertEqual(build.unsupported_claims, [])
        self.assertTrue(build.validation.ok)


if __name__ == "__main__":
    unittest.main()
