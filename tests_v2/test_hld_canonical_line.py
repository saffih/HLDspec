from __future__ import annotations

import unittest

from hldspec import hld_canonical_line as canon
from hldspec import engineering_selection as es


HLD_011_LINE = (
    'HLD-011 is out-of-scope governance at low risk, touching none; '
    '"sockets, HTTP API, web UI deliberately stripped".'
)
HLD_009_LINE = (
    'HLD-009 is in-scope api at high risk, touching cli and api; '
    '"the flow CLI verbs are the runner contract".'
)


class ParseAndValidateTests(unittest.TestCase):
    def test_parses_frame_into_normalized_record(self):
        rec = canon.parse_canonical_line(HLD_011_LINE)
        self.assertEqual(rec["id"], "HLD-011")
        self.assertEqual(rec["scope"], "out_of_scope")   # hyphen normalized
        self.assertEqual(rec["role"], "governance")
        self.assertEqual(rec["risk"], "low")
        self.assertEqual(rec["surfaces"], [])            # "none" -> empty
        self.assertIn("deliberately stripped", rec["evidence"])

    def test_parses_multiple_surfaces(self):
        rec = canon.parse_canonical_line(HLD_009_LINE)
        self.assertEqual(rec["surfaces"], ["cli", "api"])

    def test_non_matching_line_returns_none(self):
        self.assertIsNone(canon.parse_canonical_line("just some prose"))

    def test_round_trip_render_then_parse(self):
        rec = canon.parse_canonical_line(HLD_009_LINE)
        again = canon.parse_canonical_line(canon.render_canonical_line(rec))
        for key in ("id", "scope", "role", "risk", "surfaces"):
            self.assertEqual(rec[key], again[key])

    def test_legal_terms_pass_validation(self):
        rec = canon.parse_canonical_line(HLD_011_LINE)
        self.assertEqual(canon.validate_record(rec), [])

    def test_unknown_term_is_flagged_not_accepted(self):
        # closed vocabulary: a made-up scope must be reported
        rec = canon.parse_canonical_line(
            'HLD-099 is maybe-scope api at low risk, touching api; "x".'
        )
        errors = canon.validate_record(rec)
        self.assertTrue(any("scope" in e and "maybe_scope" in e for e in errors))

    def test_unknown_surface_is_flagged(self):
        rec = canon.parse_canonical_line(
            'HLD-099 is in-scope api at low risk, touching quantum; "x".'
        )
        errors = canon.validate_record(rec)
        self.assertTrue(any("surface" in e and "quantum" in e for e in errors))


# HLD-009 here is deliberately a non-api in-scope section, so the ONLY api/HTTP
# mention in the fixture lives in the out_of_scope HLD-011 section.
HLD_FIXTURE = """## HLD-009 - Runner loop

HLD-ID: HLD-009
HLD-DESC: HLD-009 is in-scope processing at low risk, touching cli; "the flow verbs are the runner loop".

The flow command-line interface is the runner loop.

## HLD-011 - Out of scope

HLD-ID: HLD-011
HLD-DESC: {line}

Sockets and an HTTP API are excluded on purpose.
""".format(line=HLD_011_LINE)


class StripExcludedTests(unittest.TestCase):
    def test_strips_out_of_scope_section_keeps_others(self):
        stripped = canon.strip_excluded_sections(HLD_FIXTURE)
        self.assertIn("HLD-009", stripped)
        self.assertNotIn("HTTP API", stripped)          # the excluded section body is gone
        self.assertNotIn("Sockets", stripped)

    def test_no_desc_lines_is_unchanged(self):
        plain = "## HLD-001 - Thing\n\nHLD-ID: HLD-001\n\nAn HTTP API exists.\n"
        self.assertEqual(canon.strip_excluded_sections(plain), plain)


class EngineeringSelectionScopeTests(unittest.TestCase):
    def test_excluded_http_does_not_trigger_http_card(self):
        # HTTP/API live ONLY in the out_of_scope section -> http_json must not fire.
        triggers = es.detect_engineering_triggers(HLD_FIXTURE)
        self.assertFalse(triggers["api.http_json"])

    def test_in_scope_surface_still_triggers(self):
        in_scope = (
            '## HLD-009 - CLI\n\nHLD-ID: HLD-009\nHLD-DESC: '
            'HLD-009 is in-scope api at high risk, touching api; "exposes an HTTP API".\n\n'
            'The service exposes an HTTP API.\n'
        )
        triggers = es.detect_engineering_triggers(in_scope)
        self.assertTrue(triggers["api.http_json"])


def _section(sid, desc, prose):
    return f"## {sid} - x\n\nHLD-ID: {sid}\nHLD-DESC: {desc}\n\n{prose}\n"


# Fully marked: every section has an HLD-DESC line.
FULL_MARKED = (
    _section("HLD-001",
             'HLD-001 is in-scope processing at high risk, touching data and processing; "core over SQLite".',
             "Core domain logic.")
    + _section("HLD-009",
               'HLD-009 is in-scope api at high risk, touching cli; "the flow CLI verbs".',
               "The runner uses an HTTP API endpoint returning JSON.")  # prose must be IGNORED in surface mode
    + _section("HLD-011",
               'HLD-011 is out-of-scope governance at low risk, touching none; "HTTP API stripped".',
               "Excluded on purpose.")
)


class SurfaceDrivenSelectionTests(unittest.TestCase):
    def ids(self, hld_text):
        return {c["id"] for c in es.select_p0_cards(hld_text)}

    def test_prose_http_api_ignored_when_fully_marked(self):
        # HLD-009 prose says "HTTP API ... JSON" but its declared surface is cli only.
        ids = self.ids(FULL_MARKED)
        self.assertNotIn("api.http_json", ids)              # prose ignored
        self.assertIn("data.schema_discipline", ids)        # from data surface
        self.assertIn("testing.contract_boundary", ids)     # from cli/data
        # modularity is not surface-derivable, so it is NOT selected in surface mode
        self.assertNotIn("architecture.modular_boundaries", ids)

    def test_declaring_api_surface_selects_http_json(self):
        marked = FULL_MARKED.replace("touching cli;", "touching cli and api;")
        self.assertIn("api.http_json", self.ids(marked))

    def test_baseline_always_selected_in_surface_mode(self):
        ids = self.ids(FULL_MARKED)
        for baseline in es.BASELINE_CARDS:
            self.assertIn(baseline, ids)

    def test_partial_marking_falls_back_to_keywords(self):
        # Drop HLD-001's DESC -> not fully marked -> keyword mode -> HLD-009 prose
        # "HTTP API" triggers http_json again (the fallback path is preserved).
        partial = FULL_MARKED.replace(
            'HLD-DESC: HLD-001 is in-scope processing at high risk, touching data and processing; "core over SQLite".\n',
            "",
        )
        self.assertIn("api.http_json", self.ids(partial))


if __name__ == "__main__":
    unittest.main()
