"""Tests for Journey 2 HLD coverage ledger contracts."""
from __future__ import annotations

import unittest
from typing import Any

from hldspec import journey2_hld_coverage_contracts as cov


def _item(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "hld_item_id": "HLD-001",
        "source_section": "§1 Overview",
        "source_text": "The system shall authenticate users.",
        "item_type": cov.ITEM_REQUIREMENT,
        "status": cov.STATUS_COVERED_IN_SDD,
        "sdd_section": "auth-design",
        "design_decision": "Use OAuth 2.0 with PKCE",
        "research_required": False,
        "research_evidence": None,
        "clarification_required": False,
        "assumption": None,
        "acceptance_criteria": "User can log in via SSO",
        "test_mapping": "test_auth_sso",
        "risk": cov.RISK_MEDIUM,
    }
    base.update(overrides)
    return base


class ValidCoverageItemTests(unittest.TestCase):
    def test_valid_covered_item_passes(self) -> None:
        item = _item()
        result = cov.validate_coverage_item(item)
        self.assertEqual(result["hld_item_id"], "HLD-001")

    def test_all_item_types_are_accepted(self) -> None:
        for item_type in cov.VALID_ITEM_TYPES:
            result = cov.validate_coverage_item(_item(item_type=item_type))
            self.assertEqual(result["item_type"], item_type)

    def test_all_statuses_are_accepted_when_constraints_met(self) -> None:
        variants = {
            cov.STATUS_COVERED_IN_SDD: {},
            cov.STATUS_NOT_COVERED: {},
            cov.STATUS_BLOCKED_BY_PRODUCT_DECISION: {},
            cov.STATUS_NEEDS_CLARIFICATION: {"clarification_required": True},
            cov.STATUS_RESEARCH_REQUIRED: {"research_required": True},
            cov.STATUS_OUT_OF_SCOPE: {"assumption": "Not in MVP scope"},
        }
        for status, extra in variants.items():
            result = cov.validate_coverage_item(_item(status=status, **extra))
            self.assertEqual(result["status"], status)

    def test_risk_levels_are_all_accepted(self) -> None:
        for risk in cov.VALID_RISK_LEVELS:
            result = cov.validate_coverage_item(_item(risk=risk))
            self.assertEqual(result["risk"], risk)

    def test_item_without_risk_passes(self) -> None:
        result = cov.validate_coverage_item(_item(risk=None))
        self.assertIsNone(result["risk"])


class InvalidItemTypeTests(unittest.TestCase):
    def test_unknown_item_type_rejected(self) -> None:
        with self.assertRaises(cov.InvalidCoverageItemError) as ctx:
            cov.validate_coverage_item(_item(item_type="BANANA"))
        self.assertIn("BANANA", str(ctx.exception))

    def test_none_item_type_rejected(self) -> None:
        with self.assertRaises(cov.InvalidCoverageItemError):
            cov.validate_coverage_item(_item(item_type=None))


class InvalidStatusTests(unittest.TestCase):
    def test_unknown_status_rejected(self) -> None:
        with self.assertRaises(cov.InvalidCoverageItemError) as ctx:
            cov.validate_coverage_item(_item(status="DONE"))
        self.assertIn("DONE", str(ctx.exception))

    def test_none_status_rejected(self) -> None:
        with self.assertRaises(cov.InvalidCoverageItemError):
            cov.validate_coverage_item(_item(status=None))


class MissingFieldTests(unittest.TestCase):
    def test_missing_hld_item_id_rejected(self) -> None:
        with self.assertRaises(cov.InvalidCoverageItemError):
            cov.validate_coverage_item(_item(hld_item_id=""))

    def test_missing_source_section_rejected(self) -> None:
        with self.assertRaises(cov.InvalidCoverageItemError):
            cov.validate_coverage_item(_item(source_section=""))

    def test_every_item_must_have_a_status(self) -> None:
        item = _item()
        del item["status"]
        with self.assertRaises(cov.InvalidCoverageItemError):
            cov.validate_coverage_item(item)


class NotCoveredDetectionTests(unittest.TestCase):
    def test_not_covered_is_a_blocker(self) -> None:
        ledger = [_item(status=cov.STATUS_NOT_COVERED)]
        blockers = cov.blocking_items(ledger)
        self.assertEqual(len(blockers), 1)
        self.assertEqual(blockers[0]["hld_item_id"], "HLD-001")

    def test_covered_is_not_a_blocker(self) -> None:
        ledger = [_item(status=cov.STATUS_COVERED_IN_SDD)]
        self.assertEqual(cov.blocking_items(ledger), [])


class NeedsClarificationTests(unittest.TestCase):
    def test_needs_clarification_is_explicit(self) -> None:
        ledger = [
            _item(
                status=cov.STATUS_NEEDS_CLARIFICATION,
                clarification_required=True,
            )
        ]
        result = cov.needs_clarification_items(ledger)
        self.assertEqual(len(result), 1)

    def test_needs_clarification_cannot_be_hidden(self) -> None:
        with self.assertRaises(cov.InvalidCoverageItemError) as ctx:
            cov.validate_coverage_item(
                _item(
                    status=cov.STATUS_NEEDS_CLARIFICATION,
                    clarification_required=False,
                )
            )
        self.assertIn("clarification_required", str(ctx.exception))


class ResearchRequiredTests(unittest.TestCase):
    def test_research_required_is_explicit(self) -> None:
        ledger = [
            _item(status=cov.STATUS_RESEARCH_REQUIRED, research_required=True)
        ]
        result = cov.research_required_items(ledger)
        self.assertEqual(len(result), 1)

    def test_research_required_cannot_be_hidden(self) -> None:
        with self.assertRaises(cov.InvalidCoverageItemError) as ctx:
            cov.validate_coverage_item(
                _item(
                    status=cov.STATUS_RESEARCH_REQUIRED,
                    research_required=False,
                )
            )
        self.assertIn("research_required", str(ctx.exception))


class OutOfScopeTests(unittest.TestCase):
    def test_out_of_scope_requires_explicit_decision(self) -> None:
        with self.assertRaises(cov.InvalidCoverageItemError) as ctx:
            cov.validate_coverage_item(
                _item(
                    status=cov.STATUS_OUT_OF_SCOPE,
                    assumption="",
                    design_decision="",
                )
            )
        self.assertIn("OUT_OF_SCOPE", str(ctx.exception))

    def test_out_of_scope_with_assumption_passes(self) -> None:
        result = cov.validate_coverage_item(
            _item(
                status=cov.STATUS_OUT_OF_SCOPE,
                assumption="Deferred to Phase 2",
            )
        )
        self.assertEqual(result["status"], cov.STATUS_OUT_OF_SCOPE)

    def test_out_of_scope_with_design_decision_passes(self) -> None:
        result = cov.validate_coverage_item(
            _item(
                status=cov.STATUS_OUT_OF_SCOPE,
                design_decision="Explicitly excluded per product owner",
            )
        )
        self.assertEqual(result["status"], cov.STATUS_OUT_OF_SCOPE)


class IncompleteLedgerTests(unittest.TestCase):
    def test_ledger_reports_incomplete_items(self) -> None:
        ledger = cov.validate_coverage_ledger([
            _item(hld_item_id="HLD-001", status=cov.STATUS_COVERED_IN_SDD),
            _item(hld_item_id="HLD-002", status=cov.STATUS_NOT_COVERED),
            _item(
                hld_item_id="HLD-003",
                status=cov.STATUS_NEEDS_CLARIFICATION,
                clarification_required=True,
            ),
        ])
        inc = cov.incomplete_items(ledger)
        ids = [i["hld_item_id"] for i in inc]
        self.assertIn("HLD-002", ids)
        self.assertIn("HLD-003", ids)
        self.assertNotIn("HLD-001", ids)


class CompletenessReportTests(unittest.TestCase):
    def test_all_covered_report(self) -> None:
        inventory = [
            {"hld_item_id": "HLD-001", "source_section": "§1", "item_type": cov.ITEM_REQUIREMENT},
        ]
        ledger = [_item(hld_item_id="HLD-001", status=cov.STATUS_COVERED_IN_SDD)]
        report = cov.build_completeness_report(inventory, ledger)
        self.assertTrue(report.all_items_inventoried)
        self.assertTrue(report.all_covered)
        self.assertEqual(report.covered_count, 1)
        self.assertEqual(report.not_covered_count, 0)

    def test_not_all_covered_report(self) -> None:
        inventory = [
            {"hld_item_id": "HLD-001", "source_section": "§1", "item_type": cov.ITEM_REQUIREMENT},
            {"hld_item_id": "HLD-002", "source_section": "§2", "item_type": cov.ITEM_NFR},
        ]
        ledger = [
            _item(hld_item_id="HLD-001", status=cov.STATUS_COVERED_IN_SDD),
            _item(hld_item_id="HLD-002", status=cov.STATUS_NOT_COVERED),
        ]
        report = cov.build_completeness_report(inventory, ledger)
        self.assertTrue(report.all_items_inventoried)
        self.assertFalse(report.all_covered)
        self.assertEqual(report.not_covered_count, 1)

    def test_unlinked_sdd_sections_detected(self) -> None:
        ledger = [_item(hld_item_id="HLD-001", sdd_section="auth-design")]
        sdd_sections = ["auth-design", "invented-section"]
        report = cov.build_completeness_report([], ledger, sdd_sections)
        self.assertEqual(report.unlinked_sections, ["invented-section"])


class AuthorityBoundaryTests(unittest.TestCase):
    def test_contracts_grant_no_approval_authority(self) -> None:
        auth = cov.journey2_coverage_authority_profile()
        self.assertFalse(auth["grants_approval_authority"])

    def test_contracts_grant_no_implementation_authority(self) -> None:
        auth = cov.journey2_coverage_authority_profile()
        self.assertFalse(auth["authorizes_implementation"])
        self.assertFalse(auth["authorizes_work_orders"])

    def test_contracts_grant_no_speckit_authority(self) -> None:
        auth = cov.journey2_coverage_authority_profile()
        self.assertFalse(auth["invokes_speckit"])

    def test_forbidden_actions_listed(self) -> None:
        auth = cov.journey2_coverage_authority_profile()
        self.assertIn("invoke SpecKit", auth["forbidden_actions"])
        self.assertIn("grant approval authority", auth["forbidden_actions"])


class NoPurityViolationTests(unittest.TestCase):
    """Verify the contracts module has no IO/subprocess/network/CLI imports."""

    def test_no_io_imports_in_contracts(self) -> None:
        import inspect
        source = inspect.getsource(cov)
        forbidden = [
            "import os", "import subprocess", "import requests",
            "import urllib", "import pathlib", "from pathlib",
            "import click", "import argparse", "import typer",
        ]
        for pattern in forbidden:
            self.assertNotIn(
                pattern, source,
                f"contracts module must not contain {pattern!r}",
            )


class RequirementInventoryTests(unittest.TestCase):
    def test_valid_inventory(self) -> None:
        inventory = [
            {"hld_item_id": "HLD-001", "source_section": "§1", "item_type": cov.ITEM_REQUIREMENT},
            {"hld_item_id": "HLD-002", "source_section": "§2", "item_type": cov.ITEM_NFR},
        ]
        result = cov.validate_requirement_inventory(inventory)
        self.assertEqual(len(result), 2)

    def test_duplicate_ids_rejected(self) -> None:
        inventory = [
            {"hld_item_id": "HLD-001", "source_section": "§1", "item_type": cov.ITEM_REQUIREMENT},
            {"hld_item_id": "HLD-001", "source_section": "§2", "item_type": cov.ITEM_NFR},
        ]
        with self.assertRaises(cov.InvalidCoverageItemError) as ctx:
            cov.validate_requirement_inventory(inventory)
        self.assertIn("duplicate", str(ctx.exception))

    def test_non_list_inventory_rejected(self) -> None:
        with self.assertRaises(cov.InvalidCoverageItemError):
            cov.validate_requirement_inventory("not a list")


if __name__ == "__main__":
    unittest.main()
