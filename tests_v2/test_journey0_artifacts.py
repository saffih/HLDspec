"""Tests for Journey 0 typed artifact models."""
from __future__ import annotations

import inspect
import unittest
from dataclasses import FrozenInstanceError

from hldspec import journey0_artifacts as artifacts


def _evidence_item(label: artifacts.EvidenceLabel) -> artifacts.EvidenceItem:
    return artifacts.EvidenceItem(
        evidence_id="E-1",
        source_type="old_speckit_spec",
        source_ref="specs/old/spec.md",
        source_location="specs/old/spec.md:1",
        summary="Old spec says run state is local",
        label=label,
        confidence="medium",
        related_items=("PD-1",),
    )


class Journey0ArtifactModelTests(unittest.TestCase):
    def test_all_artifact_models_construct_with_valid_fields(self) -> None:
        evidence = _evidence_item(artifacts.EvidenceLabel.OBSERVED)
        pack = artifacts.BrownfieldEvidencePack(evidence=(evidence,))
        surface = artifacts.ProductSurfaceMap(
            observed_capabilities=("claim task",),
            observed_users_or_actors=("operator",),
            observed_inputs_outputs=("cli -> sqlite",),
            observed_workflows=("next/done",),
            known_limits=("anonymous path exists",),
            unknowns=("source of truth",),
            source_refs=("E-1",),
        )
        spec_inventory = artifacts.SpecInventory(
            specs=(
                artifacts.SpecInventoryItem(
                    spec_id="OLD-1",
                    location="specs/old/spec.md",
                    status=artifacts.SpecStatus.STALE,
                    summary="Old broad spec",
                    covered_intent=("claiming",),
                    implementation_overlap=("partial cli",),
                    conflicts=("state ownership",),
                    source_refs=("E-1",),
                ),
            )
        )
        gap_report = artifacts.HldCodeSpecGapReport(
            gaps=(
                artifacts.GapItem(
                    gap_id="G-1",
                    gap_type=artifacts.GapType.HLD_CODE_CONFLICT,
                    description="Docs and code disagree",
                    evidence_refs=("E-1",),
                    disposition="human_decision_required",
                    required_decision_or_next_action="choose state owner",
                ),
            )
        )
        decisions = artifacts.ProductDecisionRegister(
            decisions=(
                artifacts.ProductDecision(
                    decision_id="PD-1",
                    question="Who owns run state?",
                    why_human_owned="source of truth decision",
                    options=("external controller", "local sqlite"),
                    evidence_refs=("E-1",),
                    recommended_default_if_any=None,
                    decision_status=artifacts.DecisionStatus.OPEN,
                    owner="human",
                ),
            )
        )
        verdict = artifacts.HldDraftabilityVerdict(
            verdict=artifacts.Journey0Verdict.BLOCKED,
            reason="source of truth conflict",
            blocking_items=("G-1",),
            accepted_evidence_refs=("E-1",),
            required_human_decisions=("PD-1",),
            safe_next_action="Ask human to choose state owner",
        )
        update_plan = artifacts.HldUpdatePlan(
            hld_sections_to_create_or_update=("State Ownership",),
            evidence_refs_per_section={"State Ownership": ("E-1",)},
            decisions_required_before_writing=("PD-1",),
            known_stale_material_to_exclude=("OLD-1",),
            open_questions_to_carry_forward=("state owner",),
        )

        for model in (
            pack,
            surface,
            spec_inventory,
            gap_report,
            decisions,
            verdict,
            update_plan,
        ):
            self.assertIsInstance(model.to_dict(), dict)

    def test_required_enum_values_exist(self) -> None:
        self.assertEqual(
            {label.value for label in artifacts.EvidenceLabel},
            {
                "OBSERVED",
                "INFERRED",
                "UNKNOWN",
                "CONFLICT",
                "PRODUCT_DECISION_REQUIRED",
            },
        )
        self.assertEqual(
            {verdict.value for verdict in artifacts.Journey0Verdict},
            {"PASS", "ACTION", "BLOCKED"},
        )
        self.assertEqual(
            {status.value for status in artifacts.DecisionStatus},
            {"open", "decided", "deferred"},
        )
        self.assertEqual(
            {gap_type.value for gap_type in artifacts.GapType},
            {
                "HLD_gap",
                "code_gap",
                "HLD_code_conflict",
                "stale_spec_residue",
                "safety_authority_gap",
            },
        )
        self.assertEqual(
            {status.value for status in artifacts.SpecStatus},
            {"current", "stale", "superseded", "partial", "conflicting", "unknown"},
        )

    def test_invalid_labels_and_statuses_are_rejected(self) -> None:
        with self.assertRaises(artifacts.Journey0ArtifactModelError):
            artifacts.EvidenceItem(
                evidence_id="E-1",
                source_type="code",
                source_ref="flow.py",
                source_location="flow.py:1",
                summary="bad label",
                label="OBSERVED",  # type: ignore[arg-type]
                confidence="high",
            )
        with self.assertRaises(artifacts.Journey0ArtifactModelError):
            artifacts.SpecInventoryItem(
                spec_id="OLD-1",
                location="spec.md",
                status="stale",  # type: ignore[arg-type]
                summary="bad status",
            )
        with self.assertRaises(artifacts.Journey0ArtifactModelError):
            artifacts.HldDraftabilityVerdict(
                verdict="PASS",  # type: ignore[arg-type]
                reason="bad verdict",
            )

    def test_inferred_evidence_does_not_become_authority(self) -> None:
        item = _evidence_item(artifacts.EvidenceLabel.INFERRED)

        self.assertEqual(item.label, artifacts.EvidenceLabel.INFERRED)
        self.assertFalse(item.is_authority)
        self.assertEqual(item.to_dict()["label"], "INFERRED")
        self.assertNotIn("authority", item.to_dict())

    def test_pass_is_journey0_verdict_only_without_readiness_fields(self) -> None:
        verdict = artifacts.HldDraftabilityVerdict(
            verdict=artifacts.Journey0Verdict.PASS,
            reason="accepted evidence is enough for Journey 1",
            accepted_evidence_refs=("E-1",),
            safe_next_action="Enter Journey 1 HLD hardening",
        )
        serialized = verdict.to_dict()

        self.assertEqual(serialized["verdict"], "PASS")
        self.assertTrue(verdict.journey1_only)
        self.assertFalse(verdict.implementation_ready)
        for forbidden_field in (
            "journey2_ready",
            "journey3_ready",
            "implementation_ready",
            "speckit_ready",
        ):
            self.assertNotIn(forbidden_field, serialized)

    def test_old_speckit_specs_remain_inventory_not_backlog(self) -> None:
        statuses = (
            artifacts.SpecStatus.STALE,
            artifacts.SpecStatus.PARTIAL,
            artifacts.SpecStatus.CONFLICTING,
        )
        inventory = artifacts.SpecInventory(
            specs=tuple(
                artifacts.SpecInventoryItem(
                    spec_id=f"OLD-{idx}",
                    location=f"specs/old/{idx}.md",
                    status=status,
                    summary="old SpecKit evidence",
                )
                for idx, status in enumerate(statuses)
            )
        )
        serialized = inventory.to_dict()

        self.assertEqual(
            [item["status"] for item in serialized["specs"]],
            ["stale", "partial", "conflicting"],
        )
        self.assertTrue(all(not item.becomes_backlog for item in inventory.specs))
        self.assertNotIn("backlog", serialized)

    def test_serialization_preserves_exact_labels_and_statuses(self) -> None:
        evidence = _evidence_item(artifacts.EvidenceLabel.PRODUCT_DECISION_REQUIRED)
        decision = artifacts.ProductDecision(
            decision_id="PD-1",
            question="Which behavior is canonical?",
            why_human_owned="product meaning",
            options=("a", "b"),
            evidence_refs=("E-1",),
            recommended_default_if_any="a",
            decision_status=artifacts.DecisionStatus.DEFERRED,
            owner=None,
        )
        gap = artifacts.GapItem(
            gap_id="G-1",
            gap_type=artifacts.GapType.SAFETY_AUTHORITY_GAP,
            description="approval owner unclear",
        )

        self.assertEqual(evidence.to_dict()["label"], "PRODUCT_DECISION_REQUIRED")
        self.assertEqual(decision.to_dict()["decision_status"], "deferred")
        self.assertEqual(gap.to_dict()["gap_type"], "safety_authority_gap")

    def test_result_dataclasses_are_frozen(self) -> None:
        item = _evidence_item(artifacts.EvidenceLabel.OBSERVED)

        with self.assertRaises(FrozenInstanceError):
            item.summary = "changed"  # type: ignore[misc]

    def test_module_has_no_collectors_or_runtime_io(self) -> None:
        source = inspect.getsource(artifacts)

        forbidden_tokens = (
            "open(",
            "read_text",
            "write_text",
            "Path(",
            "subprocess",
            "argparse",
            "click",
            "SpecKit",
            "collect_",
            "classify_",
            "evaluate_",
            "compute_",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
