from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import hld_map


VALID_HLD = """# Project HLD

```md
## HLD-999 - Fenced Example
HLD-ID: HLD-999
This section REF HLD-998.
```

## HLD-001 - Governance

HLD-ID: HLD-001
HLD-ROLE: governance
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: .specify/memory/constitution.md
HLD-VERIFY: generated specs preserve HLD anchors

This section REF HLD-002 for implementation context.

## HLD-002 - Sync Engine

HLD-ID: HLD-002
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: 001,002
HLD-RESOURCES: hld_spec_sync.py,specs/*/spec.md

This section DEPENDS REF HLD-001 because governance defines allowed writes.
This section BLOCKED_BY REF HLD-003 until rollout is approved.
This section CONFLICTS_WITH REF HLD-004 because rollback authority differs.

## HLD-003 - Rollout

HLD-ID: HLD-003
HLD-ROLE: operations
HLD-STATUS: planned
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD

## HLD-004 - Rollback

HLD-ID: HLD-004
HLD-ROLE: operations
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD
"""


class HldMapTests(unittest.TestCase):
    def test_parse_headings_metadata_refs_and_line_ranges(self) -> None:
        parsed = hld_map.parse_hld_text(VALID_HLD, source_path="HLD.md")

        self.assertEqual([], parsed.validation_errors)
        self.assertEqual(["HLD-001", "HLD-002", "HLD-003", "HLD-004"], [s.id for s in parsed.sections])
        self.assertEqual("Governance", parsed.sections[0].title)
        self.assertEqual("HIGH", parsed.sections[0].metadata_value("HLD-RISK"))
        self.assertEqual(["HLD-002"], parsed.sections[0].normal_refs())
        self.assertEqual(["HLD-001"], parsed.sections[1].refs_by_kind("DEPENDS"))
        self.assertEqual(["HLD-003"], parsed.sections[1].refs_by_kind("BLOCKED_BY"))
        self.assertEqual(["HLD-004"], parsed.sections[1].refs_by_kind("CONFLICTS_WITH"))
        self.assertLess(parsed.sections[0].line_start, parsed.sections[0].line_end)
        self.assertEqual(parsed.sections[0].line_end + 1, parsed.sections[1].line_start)

    def test_ignores_fenced_hld_examples(self) -> None:
        parsed = hld_map.parse_hld_text(VALID_HLD)

        ids = [section.id for section in parsed.sections]
        self.assertNotIn("HLD-999", ids)
        all_refs = [ref.target for section in parsed.sections for ref in section.references]
        self.assertNotIn("HLD-998", all_refs)

    def test_validator_catches_duplicate_ids(self) -> None:
        text = """## HLD-001 - One

HLD-ID: HLD-001
HLD-ROLE: purpose
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD

## HLD-001 - Duplicate

HLD-ID: HLD-001
HLD-ROLE: purpose
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD
"""
        parsed = hld_map.parse_hld_text(text)

        self.assertTrue(any("duplicate HLD-ID" in error for error in parsed.validation_errors))

    def test_validator_catches_missing_refs(self) -> None:
        text = """## HLD-001 - One

HLD-ID: HLD-001
HLD-ROLE: purpose
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD

This section REF HLD-404.
"""
        parsed = hld_map.parse_hld_text(text)

        self.assertTrue(any("unknown HLD-404" in error for error in parsed.validation_errors))

    def test_tbd_nearby_allows_missing_refs(self) -> None:
        text = """## HLD-001 - One

HLD-ID: HLD-001
HLD-ROLE: purpose
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD

This section REF HLD-404.
TBD: target section not assigned yet.
"""
        parsed = hld_map.parse_hld_text(text)

        self.assertFalse(any("unknown HLD-404" in error for error in parsed.validation_errors))

    def test_cycles_are_detected(self) -> None:
        text = """## HLD-001 - One

HLD-ID: HLD-001
HLD-ROLE: purpose
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD

This section DEPENDS REF HLD-002.

## HLD-002 - Two

HLD-ID: HLD-002
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD

This section DEPENDS REF HLD-001.
"""
        parsed = hld_map.parse_hld_text(text)

        self.assertEqual([["HLD-001", "HLD-002", "HLD-001"]], parsed.cycles)
        self.assertTrue(any("reference cycle detected" in error for error in parsed.validation_errors))

    def test_generated_section_files_match_source_hld_content(self) -> None:
        parsed = hld_map.parse_hld_text(VALID_HLD, source_path="HLD.md")
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            outputs = hld_map.write_hld_map_outputs(parsed, workspace)

            self.assertTrue((workspace / outputs["map"]).exists())
            self.assertTrue((workspace / outputs["index"]).exists())
            section_path = workspace / outputs["sections"]["HLD-002"]
            self.assertEqual(parsed.section_by_id()["HLD-002"].text, section_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
