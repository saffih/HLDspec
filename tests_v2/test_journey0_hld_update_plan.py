"""Tests for Journey 0 HLD update plan generation."""
from __future__ import annotations

import inspect
import unittest

from hldspec import journey0_hld_update_plan as update_plan
from hldspec.journey0_artifacts import (
    BrownfieldEvidencePack,
    DecisionStatus,
    EvidenceItem,
    EvidenceLabel,
    GapItem,
    GapType,
    HldCodeSpecGapReport,
    HldDraftabilityVerdict,
    HldUpdatePlan,
    Journey0Verdict,
    ProductDecision,
    ProductDecisionRegister,
    ProductSurfaceMap,
    SpecInventory,
    SpecInventoryItem,
    SpecStatus,
)


def _evidence(
    evidence_id: str,
    *,
    source_type: str = "product_capability",
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        source_type=source_type,
        source_ref=f"{evidence_id}.md",
        source_location=f"{evidence_id}.md:1",
        summary=f"{evidence_id} observed",
        label=EvidenceLabel.OBSERVED,
        confidence="high",
    )


def _verdict(
    verdict: Journey0Verdict = Journey0Verdict.PASS,
    *,
    accepted: tuple[str, ...] = ("E-1",),
    blocking: tuple[str, ...] = (),
    required: tuple[str, ...] = (),
) -> HldDraftabilityVerdict:
    return HldDraftabilityVerdict(
        verdict=verdict,
        reason="test verdict",
        blocking_items=blocking,
        accepted_evidence_refs=accepted,
        required_human_decisions=required,
        safe_next_action="test next action",
    )


def _plan(
    *,
    draftability_verdict: HldDraftabilityVerdict | None = None,
    evidence_pack: BrownfieldEvidencePack | None = None,
    product_surface_map: ProductSurfaceMap | None = None,
    spec_inventory: SpecInventory | None = None,
    gap_report: HldCodeSpecGapReport | None = None,
    decision_register: ProductDecisionRegister | None = None,
) -> HldUpdatePlan:
    return update_plan.build_journey0_hld_update_plan(
        draftability_verdict=draftability_verdict or _verdict(),
        evidence_pack=evidence_pack
        or BrownfieldEvidencePack(evidence=(_evidence("E-1"),)),
        product_surface_map=product_surface_map
        or ProductSurfaceMap(
            observed_capabilities=("User can claim work",),
            source_refs=("E-1",),
        ),
        spec_inventory=spec_inventory or SpecInventory(),
        gap_report=gap_report or HldCodeSpecGapReport(),
        decision_register=decision_register or ProductDecisionRegister(),
    )


class Journey0HldUpdatePlanTests(unittest.TestCase):
    def test_pass_with_product_capability_creates_product_capabilities_section(self) -> None:
        plan = _plan()

        self.assertEqual(plan.hld_sections_to_create_or_update, ("Product capabilities",))

    def test_pass_with_actor_creates_users_and_actors_section(self) -> None:
        plan = _plan(
            draftability_verdict=_verdict(accepted=("E-1",)),
            evidence_pack=BrownfieldEvidencePack(
                evidence=(_evidence("E-1", source_type="product_actor"),)
            ),
            product_surface_map=ProductSurfaceMap(
                observed_users_or_actors=("Operator",),
                source_refs=("E-1",),
            )
        )

        self.assertEqual(plan.hld_sections_to_create_or_update, ("Users and actors",))

    def test_pass_with_input_output_creates_inputs_and_outputs_section(self) -> None:
        plan = _plan(
            draftability_verdict=_verdict(accepted=("E-1",)),
            evidence_pack=BrownfieldEvidencePack(
                evidence=(_evidence("E-1", source_type="product_input_output"),)
            ),
            product_surface_map=ProductSurfaceMap(
                observed_inputs_outputs=("CLI input -> task row",),
                source_refs=("E-1",),
            )
        )

        self.assertEqual(plan.hld_sections_to_create_or_update, ("Inputs and outputs",))

    def test_pass_with_workflow_creates_workflows_section(self) -> None:
        plan = _plan(
            draftability_verdict=_verdict(accepted=("E-1",)),
            evidence_pack=BrownfieldEvidencePack(
                evidence=(_evidence("E-1", source_type="product_workflow"),)
            ),
            product_surface_map=ProductSurfaceMap(
                observed_workflows=("claim then complete",),
                source_refs=("E-1",),
            )
        )

        self.assertEqual(plan.hld_sections_to_create_or_update, ("Workflows",))

    def test_pass_with_known_limit_creates_known_limits_section(self) -> None:
        plan = _plan(
            draftability_verdict=_verdict(accepted=("E-1",)),
            evidence_pack=BrownfieldEvidencePack(
                evidence=(_evidence("E-1", source_type="product_limit"),)
            ),
            product_surface_map=ProductSurfaceMap(
                known_limits=("single local store",),
                source_refs=("E-1",),
            )
        )

        self.assertEqual(plan.hld_sections_to_create_or_update, ("Known limits",))

    def test_product_capabilities_section_gets_only_product_capability_refs(self) -> None:
        plan = _plan(
            draftability_verdict=_verdict(accepted=("E-1", "E-2")),
            evidence_pack=BrownfieldEvidencePack(
                evidence=(
                    _evidence("E-1", source_type="product_capability"),
                    _evidence("E-2", source_type="product_actor"),
                )
            ),
            product_surface_map=ProductSurfaceMap(
                observed_capabilities=("User can claim work",),
                source_refs=("E-1", "E-2"),
            ),
        )

        self.assertEqual(
            plan.evidence_refs_per_section["Product capabilities"],
            ("E-1",),
        )

    def test_users_and_actors_section_gets_only_product_actor_refs(self) -> None:
        plan = _plan(
            draftability_verdict=_verdict(accepted=("E-1", "E-2")),
            evidence_pack=BrownfieldEvidencePack(
                evidence=(
                    _evidence("E-1", source_type="product_capability"),
                    _evidence("E-2", source_type="product_actor"),
                )
            ),
            product_surface_map=ProductSurfaceMap(
                observed_users_or_actors=("Operator",),
                source_refs=("E-1", "E-2"),
            ),
        )

        self.assertEqual(plan.evidence_refs_per_section["Users and actors"], ("E-2",))

    def test_inputs_and_outputs_section_gets_only_product_input_output_refs(self) -> None:
        plan = _plan(
            draftability_verdict=_verdict(accepted=("E-1", "E-2")),
            evidence_pack=BrownfieldEvidencePack(
                evidence=(
                    _evidence("E-1", source_type="product_actor"),
                    _evidence("E-2", source_type="product_input_output"),
                )
            ),
            product_surface_map=ProductSurfaceMap(
                observed_inputs_outputs=("CLI input -> task row",),
                source_refs=("E-1", "E-2"),
            ),
        )

        self.assertEqual(plan.evidence_refs_per_section["Inputs and outputs"], ("E-2",))

    def test_workflows_section_gets_only_product_workflow_refs(self) -> None:
        plan = _plan(
            draftability_verdict=_verdict(accepted=("E-1", "E-2")),
            evidence_pack=BrownfieldEvidencePack(
                evidence=(
                    _evidence("E-1", source_type="product_limit"),
                    _evidence("E-2", source_type="product_workflow"),
                )
            ),
            product_surface_map=ProductSurfaceMap(
                observed_workflows=("claim then complete",),
                source_refs=("E-1", "E-2"),
            ),
        )

        self.assertEqual(plan.evidence_refs_per_section["Workflows"], ("E-2",))

    def test_known_limits_section_gets_only_product_limit_refs(self) -> None:
        plan = _plan(
            draftability_verdict=_verdict(accepted=("E-1", "E-2")),
            evidence_pack=BrownfieldEvidencePack(
                evidence=(
                    _evidence("E-1", source_type="product_workflow"),
                    _evidence("E-2", source_type="product_limit"),
                )
            ),
            product_surface_map=ProductSurfaceMap(
                known_limits=("single local store",),
                source_refs=("E-1", "E-2"),
            ),
        )

        self.assertEqual(plan.evidence_refs_per_section["Known limits"], ("E-2",))

    def test_two_fields_with_different_refs_get_section_specific_refs(self) -> None:
        plan = _plan(
            draftability_verdict=_verdict(accepted=("E-1", "E-2")),
            evidence_pack=BrownfieldEvidencePack(
                evidence=(
                    _evidence("E-1", source_type="product_capability"),
                    _evidence("E-2", source_type="product_actor"),
                )
            ),
            product_surface_map=ProductSurfaceMap(
                observed_capabilities=("User can claim work",),
                observed_users_or_actors=("Operator",),
                source_refs=("E-1", "E-2"),
            ),
        )

        self.assertEqual(
            plan.evidence_refs_per_section,
            {
                "Product capabilities": ("E-1",),
                "Users and actors": ("E-2",),
            },
        )

    def test_section_with_only_wrong_source_type_refs_is_not_created(self) -> None:
        plan = _plan(
            draftability_verdict=_verdict(accepted=("E-1",)),
            evidence_pack=BrownfieldEvidencePack(
                evidence=(_evidence("E-1", source_type="product_actor"),)
            ),
            product_surface_map=ProductSurfaceMap(
                observed_capabilities=("User can claim work",),
                source_refs=("E-1",),
            ),
        )

        self.assertEqual(plan.hld_sections_to_create_or_update, ())
        self.assertEqual(plan.evidence_refs_per_section, {})

    def test_unaccepted_refs_are_excluded_from_evidence_refs_per_section(self) -> None:
        plan = _plan(
            draftability_verdict=_verdict(accepted=("E-1",)),
            evidence_pack=BrownfieldEvidencePack(
                evidence=(
                    _evidence("E-1", source_type="product_capability"),
                    _evidence("E-2", source_type="product_capability"),
                )
            ),
            product_surface_map=ProductSurfaceMap(
                observed_capabilities=("User can claim work",),
                source_refs=("E-1", "E-2"),
            ),
        )

        self.assertEqual(
            plan.evidence_refs_per_section["Product capabilities"],
            ("E-1",),
        )

    def test_surface_refs_not_backed_by_matching_evidence_are_excluded(self) -> None:
        plan = _plan(
            draftability_verdict=_verdict(accepted=("E-1", "E-MISSING")),
            evidence_pack=BrownfieldEvidencePack(
                evidence=(_evidence("E-1", source_type="product_capability"),)
            ),
            product_surface_map=ProductSurfaceMap(
                observed_capabilities=("User can claim work",),
                source_refs=("E-MISSING",),
            ),
        )

        self.assertEqual(plan.hld_sections_to_create_or_update, ())
        self.assertEqual(plan.evidence_refs_per_section, {})

    def test_no_product_surface_refs_creates_no_sections(self) -> None:
        plan = _plan(
            product_surface_map=ProductSurfaceMap(
                observed_capabilities=("User can claim work",),
            )
        )

        self.assertEqual(plan.hld_sections_to_create_or_update, ())
        self.assertEqual(plan.evidence_refs_per_section, {})

    def test_action_carries_product_surface_unknowns_as_open_questions(self) -> None:
        plan = _plan(
            draftability_verdict=_verdict(Journey0Verdict.ACTION),
            product_surface_map=ProductSurfaceMap(unknowns=("surface unclear",)),
        )

        self.assertIn("surface unclear", plan.open_questions_to_carry_forward)

    def test_action_carries_non_blocking_gaps_as_open_questions(self) -> None:
        plan = _plan(
            draftability_verdict=_verdict(Journey0Verdict.ACTION),
            gap_report=HldCodeSpecGapReport(
                gaps=(GapItem("G-1", GapType.CODE_GAP, "missing tests"),)
            ),
        )

        self.assertIn("G-1", plan.open_questions_to_carry_forward)

    def test_blocked_verdict_creates_no_hld_sections(self) -> None:
        plan = _plan(
            draftability_verdict=_verdict(
                Journey0Verdict.BLOCKED,
                blocking=("G-1",),
                required=("PD-1",),
            )
        )

        self.assertEqual(plan.hld_sections_to_create_or_update, ())
        self.assertEqual(plan.evidence_refs_per_section, {})

    def test_blocked_verdict_carries_required_human_decisions(self) -> None:
        plan = _plan(
            draftability_verdict=_verdict(
                Journey0Verdict.BLOCKED,
                required=("PD-1",),
            )
        )

        self.assertIn("PD-1", plan.decisions_required_before_writing)

    def test_open_product_decisions_are_required_before_writing(self) -> None:
        plan = _plan(
            decision_register=ProductDecisionRegister(
                decisions=(
                    ProductDecision(
                        decision_id="PD-1",
                        question="Which behavior is canonical?",
                        why_human_owned="product meaning",
                        options=("a", "b"),
                        evidence_refs=("E-1",),
                        recommended_default_if_any=None,
                        decision_status=DecisionStatus.OPEN,
                        owner="human",
                    ),
                )
            )
        )

        self.assertIn("PD-1", plan.decisions_required_before_writing)

    def test_deferred_product_decision_is_carried_as_open_question(self) -> None:
        plan = _plan(
            decision_register=ProductDecisionRegister(
                decisions=(
                    ProductDecision(
                        decision_id="PD-1",
                        question="Which behavior is canonical?",
                        why_human_owned="product meaning",
                        options=("a", "b"),
                        evidence_refs=("E-1",),
                        recommended_default_if_any=None,
                        decision_status=DecisionStatus.DEFERRED,
                        owner="human",
                    ),
                )
            )
        )

        self.assertIn("PD-1", plan.open_questions_to_carry_forward)

    def test_stale_superseded_conflicting_specs_are_known_stale_material(self) -> None:
        plan = _plan(
            spec_inventory=SpecInventory(
                specs=(
                    SpecInventoryItem("S-1", "old.md", SpecStatus.STALE, "old"),
                    SpecInventoryItem("S-2", "old.md", SpecStatus.SUPERSEDED, "old"),
                    SpecInventoryItem("S-3", "old.md", SpecStatus.CONFLICTING, "old"),
                )
            )
        )

        self.assertEqual(
            plan.known_stale_material_to_exclude,
            ("S-1", "S-2", "S-3"),
        )

    def test_unknown_and_partial_specs_are_carried_as_open_questions(self) -> None:
        plan = _plan(
            spec_inventory=SpecInventory(
                specs=(
                    SpecInventoryItem("S-1", "old.md", SpecStatus.UNKNOWN, "old"),
                    SpecInventoryItem("S-2", "old.md", SpecStatus.PARTIAL, "old"),
                )
            )
        )

        self.assertIn("S-1", plan.open_questions_to_carry_forward)
        self.assertIn("S-2", plan.open_questions_to_carry_forward)

    def test_current_spec_inventory_does_not_become_backlog(self) -> None:
        plan = _plan(
            spec_inventory=SpecInventory(
                specs=(SpecInventoryItem("S-1", "current.md", SpecStatus.CURRENT, "current"),)
            )
        )

        self.assertFalse(plan.contains_backlog)
        self.assertEqual(plan.known_stale_material_to_exclude, ())
        self.assertNotIn("S-1", plan.open_questions_to_carry_forward)

    def test_output_type_is_hld_update_plan(self) -> None:
        self.assertIsInstance(_plan(), HldUpdatePlan)

    def test_hld_update_plan_contains_backlog_is_false(self) -> None:
        self.assertFalse(_plan().contains_backlog)

    def test_no_filesystem_or_external_tool_tokens_in_module(self) -> None:
        source = inspect.getsource(update_plan)

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
            "backlog",
            "implementation",
            "collect_journey0",
            "build_journey0_conservative_artifacts",
            "build_journey0_product_surface_map",
            "compute_journey0_draftability_verdict",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
