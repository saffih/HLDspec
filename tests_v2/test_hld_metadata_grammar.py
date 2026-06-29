from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

import hld_map

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


arch = load_module("build_hldspec_architecture_analysis", "scripts/build_hldspec_architecture_analysis.py")


def valid_section(extra_lines: str = "") -> str:
    return f"""# HLD

## HLD-009 - Session Contract

HLD-ID: HLD-009
HLD-ROLE: api
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD
{extra_lines}
"""


class HldMetadataGrammarTests(unittest.TestCase):
    def test_column_zero_known_metadata_is_parsed(self) -> None:
        parsed = hld_map.parse_hld_text(valid_section("HLD-VERIFY: CLI contract is checked\n"))

        self.assertEqual([], parsed.validation_errors)
        section = parsed.sections[0]
        self.assertEqual("HLD-009", section.metadata_value("HLD-ID"))
        self.assertEqual("CLI contract is checked", section.metadata_value("HLD-VERIFY"))

    def test_bullet_prefixed_hld_reference_is_prose_not_metadata(self) -> None:
        parsed = hld_map.parse_hld_text(
            valid_section(
                "\n### Notes\n"
                "- HLD-009: this is a prose/reference-list item, not metadata\n"
                "- HLD-VERIFY: this bullet must not become verification metadata\n"
            )
        )

        self.assertEqual([], parsed.validation_errors)
        section = parsed.sections[0]
        self.assertEqual([], section.metadata_values("HLD-VERIFY"))
        self.assertFalse(any("unknown HLD metadata key" in error for error in parsed.validation_errors))

    def test_indented_metadata_like_line_is_not_accepted_as_metadata(self) -> None:
        parsed = hld_map.parse_hld_text(
            """# HLD

## HLD-009 - Session Contract

  HLD-ID: HLD-009
HLD-ROLE: api
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD
"""
        )

        self.assertTrue(
            any("expected exactly one HLD-ID, found 0" in error for error in parsed.validation_errors),
            parsed.validation_errors,
        )

    def test_unknown_column_zero_hld_metadata_key_is_validation_error(self) -> None:
        parsed = hld_map.parse_hld_text(valid_section("HLD-ABC-009: malformed metadata-like line\n"))

        self.assertTrue(
            any("unknown HLD metadata key HLD-ABC-009" in error for error in parsed.validation_errors),
            parsed.validation_errors,
        )

    def test_numeric_anchor_label_as_column_zero_metadata_key_is_validation_error(self) -> None:
        parsed = hld_map.parse_hld_text(valid_section("HLD-009: malformed metadata-like line\n"))

        self.assertTrue(
            any("unknown HLD metadata key HLD-009" in error for error in parsed.validation_errors),
            parsed.validation_errors,
        )

    def test_architecture_analysis_uses_column_zero_metadata_only(self) -> None:
        hld_text = """# HLD

## HLD-001 - API Surface

HLD-ID: HLD-001
HLD-ROLE: purpose
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD
  HLD-DESC: HLD-001 is out-of-scope purpose at low risk, touching none; "proposal-only".

This section defines an HTTP API endpoint.
"""
        with tempfile.TemporaryDirectory() as tmp:
            hld_path = Path(tmp) / "HLD.md"
            hld_path.write_text(hld_text, encoding="utf-8")

            result = arch.build_analysis(Path(tmp), explicit_hld=str(hld_path))

        section = result["sections"][0]
        self.assertNotIn("HLD-DESC", section["metadata"])
        self.assertEqual("api_contract", section["layer"])
        self.assertTrue(section["spec_candidate"])

    def test_hld_format_documents_metadata_grammar(self) -> None:
        text = (ROOT / "HLD_FORMAT.md").read_text(encoding="utf-8")

        self.assertIn("Headings and metadata declarations must start at column 0", text)
        self.assertIn("executable `HLD-NNN` section anchors", text)
        self.assertIn("- HLD-009: prose or a reference-list item", text)
        self.assertIn("`HLD-ABC-009:`", text)


if __name__ == "__main__":
    unittest.main()
