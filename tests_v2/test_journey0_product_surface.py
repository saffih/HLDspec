"""Tests for conservative Journey 0 product-surface mapping."""
from __future__ import annotations

import inspect
import unittest

from hldspec import journey0_product_surface as product_surface
from hldspec.journey0_artifacts import (
    BrownfieldEvidencePack,
    EvidenceItem,
    EvidenceLabel,
    ProductSurfaceMap,
)


def _evidence(
    evidence_id: str,
    source_type: str,
    summary: str,
    *,
    label: EvidenceLabel = EvidenceLabel.OBSERVED,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        source_type=source_type,
        source_ref=f"{source_type}.md",
        source_location=f"{source_type}.md:1",
        summary=summary,
        label=label,
        confidence="medium",
    )


class Journey0ProductSurfaceTests(unittest.TestCase):
    def test_builder_consumes_brownfield_evidence_pack(self) -> None:
        result = product_surface.build_journey0_product_surface_map(
            BrownfieldEvidencePack()
        )

        self.assertIsInstance(result, ProductSurfaceMap)

    def test_builder_returns_product_surface_map(self) -> None:
        result = product_surface.build_journey0_product_surface_map(
            BrownfieldEvidencePack(
                evidence=(
                    _evidence("E-1", "product_capability", "User can claim work"),
                )
            )
        )

        self.assertIsInstance(result, ProductSurfaceMap)
        self.assertEqual(result.to_dict()["artifact"], "product_surface_map")

    def test_observed_product_capability_populates_observed_capabilities(self) -> None:
        result = product_surface.build_journey0_product_surface_map(
            BrownfieldEvidencePack(
                evidence=(
                    _evidence("E-1", "product_capability", "User can claim work"),
                )
            )
        )

        self.assertEqual(result.observed_capabilities, ("User can claim work",))

    def test_observed_product_actor_populates_observed_users_or_actors(self) -> None:
        result = product_surface.build_journey0_product_surface_map(
            BrownfieldEvidencePack(
                evidence=(_evidence("E-1", "product_actor", "Operator"),)
            )
        )

        self.assertEqual(result.observed_users_or_actors, ("Operator",))

    def test_observed_product_input_output_populates_observed_inputs_outputs(self) -> None:
        result = product_surface.build_journey0_product_surface_map(
            BrownfieldEvidencePack(
                evidence=(
                    _evidence("E-1", "product_input_output", "CLI input -> task row"),
                )
            )
        )

        self.assertEqual(result.observed_inputs_outputs, ("CLI input -> task row",))

    def test_observed_product_workflow_populates_observed_workflows(self) -> None:
        result = product_surface.build_journey0_product_surface_map(
            BrownfieldEvidencePack(
                evidence=(_evidence("E-1", "product_workflow", "claim then complete"),)
            )
        )

        self.assertEqual(result.observed_workflows, ("claim then complete",))

    def test_observed_product_limit_populates_known_limits(self) -> None:
        result = product_surface.build_journey0_product_surface_map(
            BrownfieldEvidencePack(
                evidence=(_evidence("E-1", "product_limit", "single local store"),)
            )
        )

        self.assertEqual(result.known_limits, ("single local store",))

    def test_file_only_evidence_does_not_create_product_capabilities(self) -> None:
        result = product_surface.build_journey0_product_surface_map(
            BrownfieldEvidencePack(
                evidence=(_evidence("E-1", "code_file", "app.py observed"),)
            )
        )

        self.assertEqual(result.observed_capabilities, ())

    def test_old_spec_evidence_does_not_create_product_capabilities(self) -> None:
        result = product_surface.build_journey0_product_surface_map(
            BrownfieldEvidencePack(
                evidence=(_evidence("E-1", "old_spec_state", "old spec observed"),)
            )
        )

        self.assertEqual(result.observed_capabilities, ())
        self.assertEqual(result.source_refs, ())

    def test_hld_fragment_does_not_become_authoritative_surface_by_default(self) -> None:
        result = product_surface.build_journey0_product_surface_map(
            BrownfieldEvidencePack(
                evidence=(_evidence("E-1", "hld_fragment", "HLD fragment observed"),)
            )
        )

        self.assertEqual(result.observed_capabilities, ())
        self.assertEqual(result.observed_workflows, ())
        self.assertEqual(result.source_refs, ())

    def test_inferred_evidence_does_not_populate_observed_surface_fields(self) -> None:
        result = product_surface.build_journey0_product_surface_map(
            BrownfieldEvidencePack(
                evidence=(
                    _evidence(
                        "E-1",
                        "product_capability",
                        "Probably claims work",
                        label=EvidenceLabel.INFERRED,
                    ),
                )
            )
        )

        self.assertEqual(result.observed_capabilities, ())
        self.assertIn("INFERRED", result.unknowns[0])

    def test_conflict_and_decision_evidence_do_not_populate_observed_surface(self) -> None:
        result = product_surface.build_journey0_product_surface_map(
            BrownfieldEvidencePack(
                evidence=(
                    _evidence(
                        "E-1",
                        "product_workflow",
                        "Workflow conflicts with code",
                        label=EvidenceLabel.CONFLICT,
                    ),
                    _evidence(
                        "E-2",
                        "product_actor",
                        "Owner must choose actor",
                        label=EvidenceLabel.PRODUCT_DECISION_REQUIRED,
                    ),
                )
            )
        )

        self.assertEqual(result.observed_workflows, ())
        self.assertEqual(result.observed_users_or_actors, ())
        self.assertIn("CONFLICT", result.unknowns[0])
        self.assertIn("PRODUCT_DECISION_REQUIRED", result.unknowns[1])

    def test_no_explicit_surface_evidence_records_unclassified_unknown(self) -> None:
        result = product_surface.build_journey0_product_surface_map(
            BrownfieldEvidencePack(
                evidence=(_evidence("E-1", "doc_file", "README observed"),)
            )
        )

        self.assertEqual(
            result.unknowns,
            ("No explicit observed product-surface evidence was classified.",),
        )

    def test_source_refs_include_only_evidence_used_by_the_map(self) -> None:
        result = product_surface.build_journey0_product_surface_map(
            BrownfieldEvidencePack(
                evidence=(
                    _evidence("E-1", "product_capability", "User can claim work"),
                    _evidence("E-2", "code_file", "app.py observed"),
                    _evidence(
                        "E-3",
                        "product_workflow",
                        "Ambiguous workflow",
                        label=EvidenceLabel.UNKNOWN,
                    ),
                )
            )
        )

        self.assertEqual(result.source_refs, ("E-1", "E-3"))

    def test_builder_does_not_compute_verdict(self) -> None:
        result = product_surface.build_journey0_product_surface_map(
            BrownfieldEvidencePack()
        ).to_dict()

        self.assertNotIn("verdict", result)
        self.assertNotIn("safe_next_action", result)

    def test_builder_does_not_produce_hld_update_plan(self) -> None:
        result = product_surface.build_journey0_product_surface_map(
            BrownfieldEvidencePack()
        ).to_dict()

        self.assertNotIn("hld_sections_to_create_or_update", result)
        self.assertNotIn("evidence_refs_per_section", result)

    def test_boundary_tokens_do_not_appear_in_product_surface_module(self) -> None:
        source = inspect.getsource(product_surface)

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
            "Journey0Verdict",
            "HldDraftabilityVerdict",
            "HldUpdatePlan",
            "collect_journey0",
            "build_journey0_conservative_artifacts",
            "backlog",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
