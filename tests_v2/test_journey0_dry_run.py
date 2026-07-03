"""Tests for the Journey 0 dry-run proof harness."""
from __future__ import annotations

import inspect
import json
import tempfile
import unittest
import hashlib
from dataclasses import fields, replace
from pathlib import Path

from hldspec import journey0_dry_run as dry_run
from hldspec.journey0_artifacts import (
    BrownfieldEvidencePack,
    DecisionStatus,
    HldCodeSpecGapReport,
    HldDraftabilityVerdict,
    HldUpdatePlan,
    Journey0Verdict,
    ProductDecision,
    ProductDecisionRegister,
    ProductSurfaceMap,
    SpecInventory,
)
from hldspec.journey0_declared_evidence import DeclaredProductSurfaceItem

FIXTURE_ROOT = (
    Path(__file__).parent / "fixtures" / "journey0_brownfield_target"
).resolve()


def _run_fixture(name: str, *allowed: str) -> dry_run.Journey0DryRunResult:
    return dry_run.run_journey0_dry_run(
        target_root=FIXTURE_ROOT / name,
        allowed_relative_paths=allowed or (".",),
    )


class Journey0DryRunTests(unittest.TestCase):
    def test_dry_run_returns_all_expected_journey0_artifacts(self) -> None:
        result = _run_fixture("pass")

        self.assertIsInstance(result.evidence_pack, BrownfieldEvidencePack)
        self.assertIsInstance(result.product_surface_map, ProductSurfaceMap)
        self.assertIsInstance(result.spec_inventory, SpecInventory)
        self.assertIsInstance(result.gap_report, HldCodeSpecGapReport)
        self.assertIsInstance(result.decision_register, ProductDecisionRegister)
        self.assertIsInstance(result.draftability_verdict, HldDraftabilityVerdict)
        self.assertIsInstance(result.hld_update_plan, HldUpdatePlan)

    def test_dry_run_output_is_artifact_only(self) -> None:
        result_fields = {field.name for field in fields(dry_run.Journey0DryRunResult)}

        self.assertEqual(
            result_fields,
            {
                "target_root",
                "evidence_pack",
                "product_surface_map",
                "spec_inventory",
                "gap_report",
                "decision_register",
                "draftability_verdict",
                "hld_update_plan",
                "before_snapshot",
                "after_snapshot",
            },
        )

    def test_fixture_before_after_snapshot_is_identical(self) -> None:
        result = _run_fixture("pass")

        self.assertTrue(result.target_unchanged)
        self.assertEqual(result.before_snapshot, result.after_snapshot)

    def test_explicit_allowed_paths_are_required(self) -> None:
        with self.assertRaises(ValueError):
            dry_run.run_journey0_dry_run(
                target_root=FIXTURE_ROOT / "pass",
                allowed_relative_paths=(),
            )

    def test_path_traversal_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            dry_run.run_journey0_dry_run(
                target_root=FIXTURE_ROOT / "pass",
                allowed_relative_paths=("../action",),
            )

    def test_unlisted_paths_are_not_collected(self) -> None:
        result = _run_fixture("action", "README.md")

        source_refs = {item.source_ref for item in result.evidence_pack.evidence}
        self.assertIn("README.md", source_refs)
        self.assertNotIn("unlisted/secret.md", source_refs)

    def test_collected_evidence_ids_are_deterministic_and_unique(self) -> None:
        result = _run_fixture("action", "README.md", "unlisted/secret.md")

        collected_ids = tuple(
            item.evidence_id
            for item in result.evidence_pack.evidence
            if item.evidence_id.startswith("COLLECTED-")
        )
        self.assertEqual(collected_ids, ("COLLECTED-001", "COLLECTED-002"))

    def test_pass_example_remains_journey1_only(self) -> None:
        result = _run_fixture("pass")

        self.assertEqual(result.draftability_verdict.verdict, Journey0Verdict.PASS)
        self.assertTrue(result.draftability_verdict.journey1_only)
        self.assertFalse(result.draftability_verdict.implementation_ready)

    def test_action_example_does_not_imply_approval(self) -> None:
        result = _run_fixture("action")

        self.assertEqual(result.draftability_verdict.verdict, Journey0Verdict.ACTION)
        self.assertNotIn("Proceed", result.draftability_verdict.safe_next_action)

    def test_structural_file_evidence_only_does_not_pass(self) -> None:
        result = _run_fixture("action", "README.md")

        self.assertEqual(result.draftability_verdict.verdict, Journey0Verdict.ACTION)

    def test_blocked_example_preserves_conflict(self) -> None:
        result = _run_fixture("blocked")

        self.assertEqual(result.draftability_verdict.verdict, Journey0Verdict.BLOCKED)
        self.assertIn("BLOCK-001", result.draftability_verdict.blocking_items)
        self.assertTrue(result.gap_report.gaps)

    def test_declared_product_surface_evidence_can_make_dry_run_pass(self) -> None:
        result = dry_run.run_journey0_dry_run(
            target_root=FIXTURE_ROOT / "action",
            allowed_relative_paths=("README.md",),
            declared_product_surface_evidence=(
                DeclaredProductSurfaceItem(
                    source_type="product_capability",
                    summary="Users can claim work from the queue.",
                    provenance="explicit run intent: user supplied capability",
                ),
            ),
        )

        self.assertEqual(result.draftability_verdict.verdict, Journey0Verdict.PASS)
        refs = [item.evidence_id for item in result.evidence_pack.evidence]
        self.assertEqual(refs, ["COLLECTED-001", "DECLARED-001"])
        self.assertEqual(
            result.product_surface_map.observed_capabilities,
            ("Users can claim work from the queue.",),
        )

    def test_conflict_marker_still_blocks_declared_pass(self) -> None:
        result = dry_run.run_journey0_dry_run(
            target_root=FIXTURE_ROOT / "blocked",
            allowed_relative_paths=(".",),
            declared_product_surface_evidence=(
                DeclaredProductSurfaceItem(
                    source_type="product_capability",
                    summary="Users can claim work from the queue.",
                    provenance="explicit run intent: user supplied capability",
                ),
            ),
        )

        self.assertEqual(result.draftability_verdict.verdict, Journey0Verdict.BLOCKED)

    def test_product_decision_required_marker_still_blocks_declared_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("Observed only\n", encoding="utf-8")
            (root / "journey0_evidence.json").write_text(
                json.dumps(
                    {
                        "evidence": [
                            {
                                "evidence_id": "DECISION-001",
                                "source_type": "product_capability",
                                "summary": "Human must choose the product behavior.",
                                "label": "PRODUCT_DECISION_REQUIRED",
                                "confidence": "high",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = dry_run.run_journey0_dry_run(
                target_root=root,
                allowed_relative_paths=(".",),
                declared_product_surface_evidence=(
                    DeclaredProductSurfaceItem(
                        source_type="product_capability",
                        summary="Users can claim work from the queue.",
                        provenance="explicit run intent: user supplied capability",
                    ),
                ),
            )

        self.assertEqual(result.draftability_verdict.verdict, Journey0Verdict.BLOCKED)
        self.assertEqual(
            result.decision_register.decisions[0].decision_status,
            DecisionStatus.OPEN,
        )

    def test_deferred_product_decision_still_blocks_draftability(self) -> None:
        result = _run_fixture("pass")
        deferred = ProductDecision(
            decision_id="PD-DEFERRED",
            question="Which product behavior is authoritative?",
            why_human_owned="source of truth decision",
            options=("hld", "code"),
            evidence_refs=result.draftability_verdict.accepted_evidence_refs,
            recommended_default_if_any=None,
            decision_status=DecisionStatus.DEFERRED,
            owner="human",
        )

        blocked = dry_run.compute_journey0_draftability_verdict(
            evidence_pack=result.evidence_pack,
            product_surface_map=result.product_surface_map,
            gap_report=result.gap_report,
            decision_register=ProductDecisionRegister(decisions=(deferred,)),
        )

        self.assertEqual(blocked.verdict, Journey0Verdict.BLOCKED)

    def test_hld_update_plan_is_plan_artifact_only(self) -> None:
        result = _run_fixture("pass")

        self.assertIsInstance(result.hld_update_plan, HldUpdatePlan)
        self.assertFalse(result.hld_update_plan.contains_backlog)
        self.assertFalse(result.hld_update_plan.contains_helper_handoff)

    def test_no_forbidden_boundary_tokens_in_module(self) -> None:
        source = inspect.getsource(dry_run)

        forbidden_tokens = (
            "subprocess",
            "argparse",
            "click",
            "SpecKit",
            "speckit",
            "git",
            "write_text",
            'open("',
            "open('",
            "backlog creation",
            "implementation",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, source)

    def test_no_target_mutation(self) -> None:
        result = _run_fixture("blocked")

        self.assertTrue(result.target_unchanged)

    def test_no_mutation_proof_hashes_exact_approved_target_file_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "README.md"
            target.write_text("approved target bytes\n", encoding="utf-8")

            result = dry_run.run_journey0_dry_run(
                target_root=root,
                allowed_relative_paths=("README.md",),
            )
            rows = dry_run.build_target_no_mutation_proof_rows(
                target_root=root,
                dry_run_result=result,
            )

        expected_sha = hashlib.sha256("approved target bytes\n".encode()).hexdigest()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].relative_path, "README.md")
        self.assertEqual(rows[0].before_sha256, expected_sha)
        self.assertEqual(rows[0].after_sha256, expected_sha)
        self.assertEqual(len(rows[0].after_sha256), 64)
        self.assertFalse(rows[0].bytes_changed)

    def test_no_mutation_proof_identifies_target_source_and_resolved_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("approved target bytes\n", encoding="utf-8")

            result = dry_run.run_journey0_dry_run(
                target_root=root,
                allowed_relative_paths=("README.md",),
            )
            rows = dry_run.build_target_no_mutation_proof_rows(
                target_root=root,
                dry_run_result=result,
            )

            self.assertEqual(rows[0].source_kind, "approved_target_file")
            self.assertEqual(rows[0].hash_source, "approved_target_path")
            self.assertEqual(rows[0].resolved_path, str((root / "README.md").resolve()))
            self.assertEqual(result.target_root, str(root.resolve()))

    def test_derived_copy_with_different_bytes_does_not_affect_target_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("approved target bytes\n", encoding="utf-8")
            derived = root / "source_package"
            derived.mkdir()
            (derived / "README.md").write_text("derived copy bytes\n", encoding="utf-8")

            result = dry_run.run_journey0_dry_run(
                target_root=root,
                allowed_relative_paths=("README.md",),
            )
            rows = dry_run.build_target_no_mutation_proof_rows(
                target_root=root,
                dry_run_result=result,
            )

        target_sha = hashlib.sha256("approved target bytes\n".encode()).hexdigest()
        derived_sha = hashlib.sha256("derived copy bytes\n".encode()).hexdigest()
        self.assertEqual(rows[0].after_sha256, target_sha)
        self.assertNotEqual(rows[0].after_sha256, derived_sha)

    def test_stale_hashes_cannot_be_rendered_as_fresh_target_proof(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("current target bytes\n", encoding="utf-8")

            result = dry_run.run_journey0_dry_run(
                target_root=root,
                allowed_relative_paths=("README.md",),
            )
            stale = dry_run.FileSnapshotEntry(
                relative_path="README.md",
                sha256=hashlib.sha256("stale report bytes\n".encode()).hexdigest(),
            )
            stale_result = replace(
                result,
                before_snapshot=(stale,),
                after_snapshot=(stale,),
            )

            with self.assertRaises(RuntimeError):
                dry_run.build_target_no_mutation_proof_rows(
                    target_root=root,
                    dry_run_result=stale_result,
                )

    def test_snapshot_proof_rejects_before_after_path_identity_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("readme\n", encoding="utf-8")
            (root / "HLD.md").write_text("hld\n", encoding="utf-8")

            result = dry_run.run_journey0_dry_run(
                target_root=root,
                allowed_relative_paths=("README.md",),
            )
            changed_result = replace(
                result,
                after_snapshot=(
                    dry_run.FileSnapshotEntry(
                        relative_path="HLD.md",
                        sha256=hashlib.sha256("hld\n".encode()).hexdigest(),
                    ),
                ),
            )

            with self.assertRaises(RuntimeError):
                dry_run.build_target_no_mutation_proof_rows(
                    target_root=root,
                    dry_run_result=changed_result,
                )

    def test_snapshot_proof_rejects_cross_target_same_bytes_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = root / "source"
            other_root = root / "other"
            source_root.mkdir()
            other_root.mkdir()
            (source_root / "README.md").write_text("same bytes\n", encoding="utf-8")
            (other_root / "README.md").write_text("same bytes\n", encoding="utf-8")

            source_result = dry_run.run_journey0_dry_run(
                target_root=source_root,
                allowed_relative_paths=("README.md",),
            )

            with self.assertRaises(RuntimeError):
                dry_run.build_target_no_mutation_proof_rows(
                    target_root=other_root,
                    dry_run_result=source_result,
                )

    def test_snapshot_proof_rejects_path_escape_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("readme\n", encoding="utf-8")
            result = dry_run.run_journey0_dry_run(
                target_root=root,
                allowed_relative_paths=("README.md",),
            )
            escaped = dry_run.FileSnapshotEntry(
                relative_path="../README.md",
                sha256=hashlib.sha256("readme\n".encode()).hexdigest(),
            )
            escaped_result = replace(
                result,
                before_snapshot=(escaped,),
                after_snapshot=(escaped,),
            )

            with self.assertRaises(ValueError):
                dry_run.build_target_no_mutation_proof_rows(
                    target_root=root,
                    dry_run_result=escaped_result,
                )

    def test_declared_evidence_preserves_no_mutation_snapshot(self) -> None:
        result = dry_run.run_journey0_dry_run(
            target_root=FIXTURE_ROOT / "action",
            allowed_relative_paths=("README.md",),
            declared_product_surface_evidence=(
                DeclaredProductSurfaceItem(
                    source_type="product_actor",
                    summary="Operator reviews queued work.",
                    provenance="explicit run intent: user supplied actor",
                ),
            ),
        )

        self.assertTrue(result.target_unchanged)
        self.assertEqual(result.before_snapshot, result.after_snapshot)

    def test_no_journey_progression_behavior_is_exposed(self) -> None:
        result = _run_fixture("pass")

        self.assertFalse(hasattr(result, "journey1_output"))
        self.assertFalse(hasattr(result, "journey2_output"))
        self.assertFalse(hasattr(result, "journey3_output"))

    def test_fixture_evidence_is_not_real_target_evidence(self) -> None:
        result = _run_fixture("pass")

        for item in result.evidence_pack.evidence:
            self.assertNotIn("real_target", item.source_type)
            self.assertNotIn("production", item.source_type)
            self.assertFalse(item.is_authority)

    def test_evidence_summaries_contain_no_file_content(self) -> None:
        result = _run_fixture("action", "README.md", "unlisted/secret.md")

        for item in result.evidence_pack.evidence:
            if item.evidence_id.startswith("COLLECTED-"):
                self.assertNotIn("(", item.summary.split("observed:")[-1])

    def test_declared_evidence_does_not_require_reading_target_file_contents(self) -> None:
        result = dry_run.run_journey0_dry_run(
            target_root=FIXTURE_ROOT / "action",
            allowed_relative_paths=("README.md",),
            declared_product_surface_evidence=(
                DeclaredProductSurfaceItem(
                    source_type="product_workflow",
                    summary="Claim then complete work.",
                    provenance="explicit run intent: user supplied workflow",
                ),
            ),
        )

        for item in result.evidence_pack.evidence:
            if item.evidence_id.startswith("COLLECTED-"):
                self.assertNotIn("Action Fixture", item.summary)
                self.assertNotIn("secret", item.summary)


if __name__ == "__main__":
    unittest.main()
