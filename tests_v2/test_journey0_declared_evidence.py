"""Tests for Journey 0 declared product-surface evidence adapter."""
from __future__ import annotations

import inspect
import unittest

from hldspec import journey0_declared_evidence as declared_mod
from hldspec.journey0_artifacts import (
    BrownfieldEvidencePack,
    EvidenceLabel,
    Journey0ArtifactModelError,
    Journey0Verdict,
    ProductSurfaceMap,
)
from hldspec.journey0_declared_evidence import (
    DeclaredProductSurfaceItem,
    build_declared_evidence,
)
from hldspec.journey0_draftability import compute_journey0_draftability_verdict
from hldspec.journey0_product_surface import build_journey0_product_surface_map


class TestDeclaredProductSurfaceItem(unittest.TestCase):

    def test_valid_product_capability(self) -> None:
        item = DeclaredProductSurfaceItem(
            source_type="product_capability",
            summary="Users can create todo items",
            provenance="owner:alice",
        )
        self.assertEqual(item.source_type, "product_capability")

    def test_valid_product_actor(self) -> None:
        item = DeclaredProductSurfaceItem(
            source_type="product_actor",
            summary="Operator manages the system",
            provenance="kickoff:2026-07-01",
        )
        self.assertEqual(item.source_type, "product_actor")

    def test_valid_product_input_output(self) -> None:
        item = DeclaredProductSurfaceItem(
            source_type="product_input_output",
            summary="CLI input produces task rows",
            provenance="owner:bob",
        )
        self.assertEqual(item.source_type, "product_input_output")

    def test_valid_product_workflow(self) -> None:
        item = DeclaredProductSurfaceItem(
            source_type="product_workflow",
            summary="Claim then complete cycle",
            provenance="kickoff:2026-07-01",
        )
        self.assertEqual(item.source_type, "product_workflow")

    def test_valid_product_limit(self) -> None:
        item = DeclaredProductSurfaceItem(
            source_type="product_limit",
            summary="Single local store only",
            provenance="owner:alice",
        )
        self.assertEqual(item.source_type, "product_limit")

    def test_invalid_source_type_rejected(self) -> None:
        with self.assertRaises(Journey0ArtifactModelError):
            DeclaredProductSurfaceItem(
                source_type="doc_file",
                summary="Some doc",
                provenance="owner:alice",
            )

    def test_generic_code_file_source_type_rejected(self) -> None:
        with self.assertRaises(Journey0ArtifactModelError):
            DeclaredProductSurfaceItem(
                source_type="code_file",
                summary="Some code",
                provenance="owner:alice",
            )

    def test_empty_summary_rejected(self) -> None:
        with self.assertRaises(Journey0ArtifactModelError):
            DeclaredProductSurfaceItem(
                source_type="product_capability",
                summary="",
                provenance="owner:alice",
            )

    def test_whitespace_only_summary_rejected(self) -> None:
        with self.assertRaises(Journey0ArtifactModelError):
            DeclaredProductSurfaceItem(
                source_type="product_capability",
                summary="   ",
                provenance="owner:alice",
            )

    def test_summary_over_max_length_rejected(self) -> None:
        with self.assertRaises(Journey0ArtifactModelError):
            DeclaredProductSurfaceItem(
                source_type="product_capability",
                summary="x" * 281,
                provenance="owner:alice",
            )

    def test_summary_at_max_length_accepted(self) -> None:
        item = DeclaredProductSurfaceItem(
            source_type="product_capability",
            summary="x" * 280,
            provenance="owner:alice",
        )
        self.assertEqual(len(item.summary), 280)

    def test_empty_provenance_rejected(self) -> None:
        with self.assertRaises(Journey0ArtifactModelError):
            DeclaredProductSurfaceItem(
                source_type="product_capability",
                summary="Users can create items",
                provenance="",
            )

    def test_frozen(self) -> None:
        item = DeclaredProductSurfaceItem(
            source_type="product_capability",
            summary="Users can create items",
            provenance="owner:alice",
        )
        with self.assertRaises(AttributeError):
            item.source_type = "product_actor"  # type: ignore[misc]


class TestBuildDeclaredEvidence(unittest.TestCase):

    def test_empty_input_returns_empty_pack(self) -> None:
        pack = build_declared_evidence(())
        self.assertEqual(pack.evidence, ())

    def test_single_capability_produces_correct_evidence(self) -> None:
        item = DeclaredProductSurfaceItem(
            source_type="product_capability",
            summary="Users can create todo items",
            provenance="owner:alice",
        )
        pack = build_declared_evidence((item,))

        self.assertEqual(len(pack.evidence), 1)
        ev = pack.evidence[0]
        self.assertEqual(ev.evidence_id, "DECLARED-001")
        self.assertEqual(ev.source_type, "product_capability")
        self.assertEqual(ev.source_ref, "owner:alice")
        self.assertEqual(ev.source_location, "declared")
        self.assertEqual(ev.summary, "Users can create todo items")
        self.assertEqual(ev.label, EvidenceLabel.OBSERVED)
        self.assertEqual(ev.confidence, "high")

    def test_multiple_items_get_sequential_ids(self) -> None:
        items = tuple(
            DeclaredProductSurfaceItem(
                source_type="product_capability",
                summary=f"Capability {i}",
                provenance="owner:alice",
            )
            for i in range(3)
        )
        pack = build_declared_evidence(items)

        ids = [ev.evidence_id for ev in pack.evidence]
        self.assertEqual(ids, ["DECLARED-001", "DECLARED-002", "DECLARED-003"])

    def test_all_five_source_types_produce_evidence(self) -> None:
        types = [
            "product_capability",
            "product_actor",
            "product_input_output",
            "product_workflow",
            "product_limit",
        ]
        items = tuple(
            DeclaredProductSurfaceItem(
                source_type=st,
                summary=f"Observation for {st}",
                provenance="owner:alice",
            )
            for st in types
        )
        pack = build_declared_evidence(items)

        self.assertEqual(len(pack.evidence), 5)
        produced_types = [ev.source_type for ev in pack.evidence]
        self.assertEqual(produced_types, types)

    def test_label_is_always_observed(self) -> None:
        items = tuple(
            DeclaredProductSurfaceItem(
                source_type=st,
                summary=f"Obs {st}",
                provenance="owner:alice",
            )
            for st in ["product_capability", "product_actor", "product_limit"]
        )
        pack = build_declared_evidence(items)
        for ev in pack.evidence:
            self.assertEqual(ev.label, EvidenceLabel.OBSERVED)

    def test_returns_brownfield_evidence_pack(self) -> None:
        item = DeclaredProductSurfaceItem(
            source_type="product_capability",
            summary="Cap",
            provenance="owner:alice",
        )
        pack = build_declared_evidence((item,))
        self.assertIsInstance(pack, BrownfieldEvidencePack)

    def test_provenance_preserved_in_source_ref(self) -> None:
        item = DeclaredProductSurfaceItem(
            source_type="product_capability",
            summary="Cap",
            provenance="kickoff:2026-07-01",
        )
        pack = build_declared_evidence((item,))
        self.assertEqual(pack.evidence[0].source_ref, "kickoff:2026-07-01")


class TestDeclaredEvidenceEndToEndPassChain(unittest.TestCase):
    """Prove declared evidence flows through ProductSurfaceMap + draftability to PASS."""

    def _verdict_from_declared(
        self,
        items: tuple[DeclaredProductSurfaceItem, ...],
        *,
        extra_evidence: tuple = (),
    ) -> Journey0Verdict:
        pack = build_declared_evidence(items)
        merged = BrownfieldEvidencePack(
            evidence=pack.evidence + extra_evidence,
        )
        surface_map = build_journey0_product_surface_map(merged)
        from hldspec.journey0_artifacts import (
            HldCodeSpecGapReport,
            ProductDecisionRegister,
        )

        verdict = compute_journey0_draftability_verdict(
            evidence_pack=merged,
            product_surface_map=surface_map,
            decision_register=ProductDecisionRegister(decisions=()),
            gap_report=HldCodeSpecGapReport(gaps=()),
        )
        return verdict.verdict

    def test_declared_capability_reaches_pass(self) -> None:
        items = (
            DeclaredProductSurfaceItem(
                source_type="product_capability",
                summary="Users can create todo items",
                provenance="owner:alice",
            ),
        )
        self.assertEqual(self._verdict_from_declared(items), Journey0Verdict.PASS)

    def test_declared_actor_reaches_pass(self) -> None:
        items = (
            DeclaredProductSurfaceItem(
                source_type="product_actor",
                summary="Operator manages the system",
                provenance="owner:alice",
            ),
        )
        self.assertEqual(self._verdict_from_declared(items), Journey0Verdict.PASS)

    def test_declared_input_output_reaches_pass(self) -> None:
        items = (
            DeclaredProductSurfaceItem(
                source_type="product_input_output",
                summary="CLI input produces task rows",
                provenance="owner:alice",
            ),
        )
        self.assertEqual(self._verdict_from_declared(items), Journey0Verdict.PASS)

    def test_declared_workflow_reaches_pass(self) -> None:
        items = (
            DeclaredProductSurfaceItem(
                source_type="product_workflow",
                summary="Claim then complete cycle",
                provenance="owner:alice",
            ),
        )
        self.assertEqual(self._verdict_from_declared(items), Journey0Verdict.PASS)

    def test_declared_limit_reaches_pass(self) -> None:
        items = (
            DeclaredProductSurfaceItem(
                source_type="product_limit",
                summary="Single local store only",
                provenance="owner:alice",
            ),
        )
        self.assertEqual(self._verdict_from_declared(items), Journey0Verdict.PASS)

    def test_empty_declarations_cannot_reach_pass(self) -> None:
        self.assertEqual(self._verdict_from_declared(()), Journey0Verdict.ACTION)

    def test_generic_file_evidence_alone_cannot_reach_pass(self) -> None:
        from hldspec.journey0_artifacts import EvidenceItem

        generic = EvidenceItem(
            evidence_id="COLLECTED-001",
            source_type="doc_file",
            source_ref="README.md",
            source_location="./README.md",
            summary="A readme file",
            label=EvidenceLabel.OBSERVED,
            confidence="medium",
        )
        pack = BrownfieldEvidencePack(evidence=(generic,))
        surface_map = build_journey0_product_surface_map(pack)
        from hldspec.journey0_artifacts import (
            HldCodeSpecGapReport,
            ProductDecisionRegister,
        )

        verdict = compute_journey0_draftability_verdict(
            evidence_pack=pack,
            product_surface_map=surface_map,
            decision_register=ProductDecisionRegister(decisions=()),
            gap_report=HldCodeSpecGapReport(gaps=()),
        )
        self.assertEqual(verdict.verdict, Journey0Verdict.ACTION)


class TestBoundaryTokens(unittest.TestCase):

    def test_module_does_not_contain_forbidden_tokens(self) -> None:
        source = inspect.getsource(declared_mod)

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
            "HldUpdatePlan",
            "collect_journey0",
            "build_journey0_conservative_artifacts",
            "backlog",
            "Journey1",
            "journey1",
            "hld_sections",
            "agent_session",
            "command_runner",
        )
        for token in forbidden_tokens:
            self.assertNotIn(
                token, source, f"Forbidden token {token!r} found in module source"
            )

    def test_module_has_no_filesystem_io(self) -> None:
        source = inspect.getsource(declared_mod)
        io_tokens = ("os.path", "pathlib", "shutil", "glob", "scandir", "listdir")
        for token in io_tokens:
            self.assertNotIn(
                token, source, f"IO token {token!r} found in module source"
            )

    def test_evidence_is_never_authority(self) -> None:
        item = DeclaredProductSurfaceItem(
            source_type="product_capability",
            summary="Cap",
            provenance="owner:alice",
        )
        pack = build_declared_evidence((item,))
        for ev in pack.evidence:
            self.assertFalse(ev.is_authority)


if __name__ == "__main__":
    unittest.main()
