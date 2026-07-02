"""Tests for conservative Journey 0 evidence classification."""
from __future__ import annotations

import inspect
import unittest

from hldspec import journey0_classifiers as classifiers
from hldspec.journey0_artifacts import (
    BrownfieldEvidencePack,
    EvidenceItem,
    EvidenceLabel,
    HldCodeSpecGapReport,
    ProductDecisionRegister,
    SpecInventory,
    SpecStatus,
)


def _evidence(
    evidence_id: str,
    *,
    source_type: str = "doc_file",
    source_ref: str = "README.md",
    summary: str = "Observed file",
    label: EvidenceLabel = EvidenceLabel.OBSERVED,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        source_type=source_type,
        source_ref=source_ref,
        source_location=f"{source_ref}:1",
        summary=summary,
        label=label,
        confidence="medium",
    )


class Journey0ClassifierTests(unittest.TestCase):
    def test_classifier_consumes_brownfield_evidence_pack(self) -> None:
        pack = BrownfieldEvidencePack(
            evidence=(
                _evidence(
                    "E-1",
                    source_type="old_spec_state",
                    source_ref=".specify/spec.md",
                ),
            )
        )

        inventory, gap_report, decisions = (
            classifiers.build_journey0_conservative_artifacts(pack)
        )

        self.assertEqual(len(inventory.specs), 1)
        self.assertEqual(gap_report.gaps, ())
        self.assertEqual(decisions.decisions, ())

    def test_classifier_returns_only_typed_journey0_artifacts(self) -> None:
        result = classifiers.build_journey0_conservative_artifacts(
            BrownfieldEvidencePack()
        )

        self.assertIsInstance(result[0], SpecInventory)
        self.assertIsInstance(result[1], HldCodeSpecGapReport)
        self.assertIsInstance(result[2], ProductDecisionRegister)
        self.assertEqual(len(result), 3)

    def test_old_spec_evidence_becomes_spec_inventory_item(self) -> None:
        inventory, _, _ = classifiers.build_journey0_conservative_artifacts(
            BrownfieldEvidencePack(
                evidence=(
                    _evidence(
                        "E-1",
                        source_type="old_spec_state",
                        source_ref=".specify/spec.md",
                        summary="old SpecKit spec observed",
                    ),
                )
            )
        )

        self.assertEqual(len(inventory.specs), 1)
        self.assertEqual(inventory.specs[0].location, ".specify/spec.md")
        self.assertEqual(inventory.specs[0].source_refs, ("E-1",))

    def test_old_spec_status_defaults_to_unknown(self) -> None:
        inventory, _, _ = classifiers.build_journey0_conservative_artifacts(
            BrownfieldEvidencePack(
                evidence=(
                    _evidence(
                        "E-1",
                        source_type="old_spec_state",
                        source_ref="specs/old/spec.md",
                    ),
                )
            )
        )

        self.assertEqual(inventory.specs[0].status, SpecStatus.UNKNOWN)
        self.assertEqual(inventory.to_dict()["specs"][0]["status"], "unknown")

    def test_spec_inventory_does_not_become_backlog_or_authority(self) -> None:
        inventory, _, _ = classifiers.build_journey0_conservative_artifacts(
            BrownfieldEvidencePack(
                evidence=(
                    _evidence(
                        "E-1",
                        source_type="old_spec_state",
                        source_ref=".specify/spec.md",
                    ),
                )
            )
        )
        serialized = inventory.to_dict()

        self.assertFalse(inventory.specs[0].becomes_backlog)
        self.assertNotIn("backlog", serialized)
        self.assertNotIn("authority", serialized["specs"][0])

    def test_explicit_conflict_evidence_becomes_gap_without_resolution(self) -> None:
        _, gap_report, decisions = classifiers.build_journey0_conservative_artifacts(
            BrownfieldEvidencePack(
                evidence=(
                    _evidence(
                        "E-1",
                        summary="Docs and code explicitly conflict on state ownership",
                        label=EvidenceLabel.CONFLICT,
                    ),
                )
            )
        )

        self.assertEqual(len(gap_report.gaps), 1)
        self.assertEqual(gap_report.gaps[0].evidence_refs, ("E-1",))
        self.assertIn("human", gap_report.gaps[0].disposition)
        self.assertEqual(decisions.decisions, ())

    def test_product_decision_required_evidence_becomes_open_decision(self) -> None:
        _, gap_report, decisions = classifiers.build_journey0_conservative_artifacts(
            BrownfieldEvidencePack(
                evidence=(
                    _evidence(
                        "E-1",
                        source_ref="notes.md",
                        summary="Source of truth must be chosen by owner",
                        label=EvidenceLabel.PRODUCT_DECISION_REQUIRED,
                    ),
                )
            )
        )

        self.assertEqual(gap_report.gaps, ())
        self.assertEqual(len(decisions.decisions), 1)
        self.assertEqual(decisions.decisions[0].evidence_refs, ("E-1",))
        self.assertEqual(decisions.decisions[0].decision_status.value, "open")
        self.assertFalse(decisions.decisions[0].agent_approved)

    def test_simple_observed_only_fixture_has_empty_gap_and_decision_outputs(self) -> None:
        inventory, gap_report, decisions = (
            classifiers.build_journey0_conservative_artifacts(
                BrownfieldEvidencePack(
                    evidence=(
                        _evidence("E-1", source_type="code_file", source_ref="app.py"),
                    )
                )
            )
        )

        self.assertEqual(inventory.specs, ())
        self.assertEqual(gap_report.gaps, ())
        self.assertEqual(decisions.decisions, ())

    def test_classifier_does_not_compute_journey0_verdict(self) -> None:
        result = classifiers.build_journey0_conservative_artifacts(
            BrownfieldEvidencePack()
        )
        serialized = [artifact.to_dict() for artifact in result]

        self.assertNotIn("verdict", str(serialized))
        self.assertNotIn("safe_next_action", str(serialized))

    def test_classifier_does_not_produce_draftability_or_update_plan(self) -> None:
        result = classifiers.build_journey0_conservative_artifacts(
            BrownfieldEvidencePack()
        )

        self.assertEqual(
            [artifact.to_dict()["artifact"] for artifact in result],
            [
                "spec_inventory",
                "hld_code_spec_gap_report",
                "product_decision_register",
            ],
        )

    def test_inferred_evidence_remains_non_authoritative(self) -> None:
        item = _evidence("E-1", label=EvidenceLabel.INFERRED)
        inventory, gap_report, decisions = (
            classifiers.build_journey0_conservative_artifacts(
                BrownfieldEvidencePack(evidence=(item,))
            )
        )

        self.assertFalse(item.is_authority)
        self.assertEqual(inventory.specs, ())
        self.assertEqual(gap_report.gaps, ())
        self.assertEqual(decisions.decisions, ())

    def test_boundary_tokens_do_not_appear_in_classifier_module(self) -> None:
        source = inspect.getsource(classifiers)

        forbidden_tokens = (
            "subprocess",
            "argparse",
            "click",
            "Path(",
            "open(",
            "read_text",
            "write_text",
            "SpecKit",
            "speckit",
            "git",
            "classify_",
            "compute_verdict",
            "draftability",
            "Journey0Verdict",
            "HldDraftabilityVerdict",
            "HldUpdatePlan",
            "backlog",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
