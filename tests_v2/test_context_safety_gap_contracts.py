"""Contract tests for Brownfield Context Safety and Gap Ledger.

Pins the load-bearing rules of
docs/HLDSPEC_BROWNFIELD_CONTEXT_SAFETY_AND_GAP_LEDGER.md:
no gap may disappear, lost coverage is a correctness failure, gaps must be
classified before build planning, BLOCKING/CONFLICT gaps make the plan unsafe,
worker receipts must be compact, evidence-not-inspected must be recorded,
RunSkeptic reconciliation is required, and the module grants no authority.
"""
from __future__ import annotations

import inspect
import types
import unittest

from hldspec import context_safety_gap_contracts as csg


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def _gap(
    gap_id: str = "G-1",
    gap_type: csg.GapType = csg.GapType.PRODUCT_GAP,
    status: csg.GapStatus = csg.GapStatus.RESOLVED_BY_EVIDENCE,
    description: str = "test gap",
    source_worker: str = "W-A",
    **kwargs,
) -> csg.GapItem:
    return csg.GapItem(
        gap_id=gap_id,
        gap_type=gap_type,
        status=status,
        description=description,
        source_worker=source_worker,
        **kwargs,
    )


def _receipt(
    worker_id: str = "W-A",
    gaps: tuple[str, ...] = ("G-1",),
    raw_size_bytes: int = 1000,
    evidence_not_inspected: tuple[str, ...] | None = ("skipped.md",),
) -> csg.WorkerReceipt:
    return csg.WorkerReceipt(
        worker_id=worker_id,
        evidence_inspected=("file_a.md",),
        findings=("finding-1",),
        gaps=gaps,
        confidence="HIGH",
        evidence_not_inspected=evidence_not_inspected,
        raw_size_bytes=raw_size_bytes,
    )


def _evidence_map(
    not_inspected: tuple[str, ...] | None = ("skipped.md",),
) -> csg.EvidenceMap:
    return csg.EvidenceMap(
        inspected=("file_a.md",),
        not_inspected=not_inspected,
    )


def _reconciliation() -> csg.RunSkepticGapReconciliation:
    return csg.RunSkepticGapReconciliation(reconciled=True)


_UNSET = object()


def _safe_verdict(
    gaps: tuple[csg.GapItem, ...] | None = None,
    receipts: tuple[csg.WorkerReceipt, ...] | None = None,
    reconciliation=_UNSET,
    evidence_map=_UNSET,
    rules: csg.ContextSafetyRules | None = None,
) -> csg.ContextSafetyVerdict:
    if gaps is None:
        gaps = (_gap(),)
    if receipts is None:
        receipts = (_receipt(),)
    if reconciliation is _UNSET:
        reconciliation = _reconciliation()
    if evidence_map is _UNSET:
        evidence_map = _evidence_map()
    return csg.context_safety_verdict(
        csg.GapLedger(gaps=gaps),
        receipts,
        reconciliation,
        evidence_map,
        rules,
    )


class ContextSafetyGapContractTests(unittest.TestCase):

    # 1. Valid gap item passes.
    def test_valid_gap_item_passes(self) -> None:
        blockers = csg.gap_item_blockers(_gap())
        self.assertEqual(blockers, [])

    # 2. Invalid gap type rejected.
    def test_invalid_gap_type_rejected(self) -> None:
        with self.assertRaises(ValueError):
            csg.GapType("NOT_A_REAL_TYPE")

    # 3. Invalid gap status rejected.
    def test_invalid_gap_status_rejected(self) -> None:
        with self.assertRaises(ValueError):
            csg.GapStatus("NOT_A_REAL_STATUS")

    # 4. No gap may remain unclassified.
    def test_unclassified_gap_blocks(self) -> None:
        v = _safe_verdict(
            gaps=(_gap(gap_type=csg.GapType.UNKNOWN),),
        )
        self.assertFalse(v.safe)
        self.assertTrue(
            any("unclassified" in b for b in v.blockers),
        )

    # 5. Missing worker gap in final ledger is detected.
    def test_missing_worker_gap_detected(self) -> None:
        receipt = _receipt(gaps=("G-1", "G-DROPPED"))
        v = _safe_verdict(
            gaps=(_gap(gap_id="G-1"),),
            receipts=(receipt,),
        )
        self.assertFalse(v.safe)
        self.assertTrue(
            any("G-DROPPED" in b and "missing" in b for b in v.blockers),
        )

    # 6. BLOCKING gap makes final plan unsafe.
    def test_blocking_gap_makes_plan_unsafe(self) -> None:
        v = _safe_verdict(
            gaps=(_gap(status=csg.GapStatus.BLOCKING),),
        )
        self.assertFalse(v.safe)
        self.assertTrue(
            any("BLOCKING" in b for b in v.blockers),
        )

    # 7. CONFLICT gap must be surfaced.
    def test_conflict_gap_surfaced(self) -> None:
        v = _safe_verdict(
            gaps=(_gap(gap_id="G-CONFLICT", status=csg.GapStatus.CONFLICT),),
        )
        self.assertFalse(v.safe)
        self.assertIn("G-CONFLICT", v.conflicts)
        self.assertTrue(
            any("CONFLICT" in b for b in v.blockers),
        )

    # 8. ASSUMED_FOR_NOW requires explicit assumption text.
    def test_assumed_for_now_requires_text(self) -> None:
        v = _safe_verdict(
            gaps=(_gap(status=csg.GapStatus.ASSUMED_FOR_NOW),),
        )
        self.assertFalse(v.safe)
        self.assertTrue(
            any("assumption_text" in b for b in v.blockers),
        )

        v_ok = _safe_verdict(
            gaps=(
                _gap(
                    status=csg.GapStatus.ASSUMED_FOR_NOW,
                    assumption_text="WAL corruption is the likely cause",
                ),
            ),
        )
        self.assertTrue(v_ok.safe)

    # 9. NEEDS_OWNER only allowed when marked blocking or owner-decision scoped.
    def test_needs_owner_requires_blocking_or_scope(self) -> None:
        # Neither blocking nor scoped → blocker
        v_bad = _safe_verdict(
            gaps=(_gap(status=csg.GapStatus.NEEDS_OWNER),),
        )
        self.assertFalse(v_bad.safe)
        self.assertTrue(
            any("NEEDS_OWNER" in b for b in v_bad.blockers),
        )

        # blocking=True → valid
        v_blocking = _safe_verdict(
            gaps=(
                _gap(status=csg.GapStatus.NEEDS_OWNER, blocking=True),
            ),
        )
        self.assertTrue(v_blocking.safe)

        # owner_decision_scope set → valid
        v_scoped = _safe_verdict(
            gaps=(
                _gap(
                    status=csg.GapStatus.NEEDS_OWNER,
                    owner_decision_scope="v1 vs v2 canonical choice",
                ),
            ),
        )
        self.assertTrue(v_scoped.safe)

    # 10. Oversized worker receipt is detected.
    def test_oversized_receipt_detected(self) -> None:
        big = _receipt(raw_size_bytes=100_000)
        v = _safe_verdict(receipts=(big,))
        self.assertFalse(v.safe)
        self.assertTrue(
            any("compactness" in b for b in v.blockers),
        )

    # 11. Evidence not inspected must be recorded.
    def test_evidence_not_inspected_must_be_recorded(self) -> None:
        # None = not recorded → blocker
        v_map = _safe_verdict(evidence_map=_evidence_map(not_inspected=None))
        self.assertFalse(v_map.safe)
        self.assertTrue(
            any("not inspected" in b.lower() for b in v_map.blockers),
        )

        # Worker with None evidence_not_inspected → blocker
        receipt_none = _receipt(evidence_not_inspected=None)
        v_worker = _safe_verdict(receipts=(receipt_none,))
        self.assertFalse(v_worker.safe)
        self.assertTrue(
            any("evidence_not_inspected" in b for b in v_worker.blockers),
        )

        # Empty tuple = recorded as empty → OK
        v_ok = _safe_verdict(
            evidence_map=_evidence_map(not_inspected=()),
            receipts=(_receipt(evidence_not_inspected=()),),
        )
        self.assertTrue(v_ok.safe)

    # 12. RunSkeptic reconciliation required before final safe verdict.
    def test_skeptic_reconciliation_required(self) -> None:
        v = _safe_verdict(reconciliation=None)
        self.assertFalse(v.safe)
        self.assertTrue(
            any("reconciliation" in b.lower() for b in v.blockers),
        )

    # 13. Owner-declared non-required evidence is SAFE_TO_DEFER but recorded.
    def test_owner_declared_not_required_remains_recorded(self) -> None:
        gap = _gap(
            gap_id="G-OLD-DOC",
            gap_type=csg.GapType.PRODUCT_GAP,
            status=csg.GapStatus.SAFE_TO_DEFER,
            description="313KB Devin doc owner-declared non-required",
        )
        receipt = _receipt(gaps=("G-OLD-DOC",))
        emap = csg.EvidenceMap(
            inspected=("HLD.md",),
            not_inspected=("skipped.md",),
            owner_declared_not_required=("old_devin_313k.md",),
        )
        v = _safe_verdict(gaps=(gap,), receipts=(receipt,), evidence_map=emap)
        self.assertTrue(v.safe)
        self.assertIn("old_devin_313k.md", emap.owner_declared_not_required)

    # 14. Authority grants are all false.
    def test_authority_grants_all_false(self) -> None:
        rules = csg.ContextSafetyRules()
        self.assertEqual(csg.authority_grants(rules), [])

        bad_rules = csg.ContextSafetyRules(grants_approval_authority=True)
        grants = csg.authority_grants(bad_rules)
        self.assertIn("approval", grants)

        v = _safe_verdict(rules=bad_rules)
        self.assertFalse(v.safe)
        self.assertTrue(
            any("Authority grants" in b for b in v.blockers),
        )

    # 15. Module is pure: no IO/child-process/network/CLI.
    def test_module_purity(self) -> None:
        forbidden_modules = {"os", "pathlib", "io", "tempfile"}
        for name, obj in vars(csg).items():
            if isinstance(obj, types.ModuleType):
                self.assertNotIn(
                    obj.__name__,
                    forbidden_modules,
                    f"Contract module imports forbidden module: {obj.__name__}",
                )

        source = inspect.getsource(csg)
        forbidden_tokens = [
            "sub" + "process", "os." + "system", "url" + "lib",
        ]
        for token in forbidden_tokens:
            self.assertNotIn(
                token, source,
                f"Contract module source contains forbidden token: {token}",
            )

    # 16. Worker decomposition required but no receipts.
    def test_worker_decomposition_required(self) -> None:
        v = _safe_verdict(receipts=())
        self.assertFalse(v.safe)
        self.assertTrue(
            any("Worker decomposition" in b for b in v.blockers),
        )

        v_ok = _safe_verdict(
            receipts=(),
            rules=csg.ContextSafetyRules(require_worker_decomposition=False),
        )
        self.assertTrue(v_ok.safe)

    # 17. Empty gap ledger is rejected when required.
    def test_empty_gap_ledger_rejected(self) -> None:
        v = _safe_verdict(gaps=(), receipts=(_receipt(gaps=()),))
        self.assertFalse(v.safe)
        self.assertTrue(
            any("ledger is required but empty" in b for b in v.blockers),
        )

    # 18. RunSkeptic reconciliation with reconciled=False blocks.
    def test_skeptic_reconciliation_failed_blocks(self) -> None:
        v = _safe_verdict(
            reconciliation=csg.RunSkepticGapReconciliation(
                reconciled=False, notes="gaps not covered",
            ),
        )
        self.assertFalse(v.safe)
        self.assertTrue(
            any("reconciliation failed" in b.lower() for b in v.blockers),
        )

    # -- Additional edge cases from Baton calibration --

    def test_lead_context_limit(self) -> None:
        big_a = _receipt(worker_id="W-A", gaps=("G-1",), raw_size_bytes=120_000)
        big_b = _receipt(worker_id="W-B", gaps=("G-2",), raw_size_bytes=120_000)
        v = _safe_verdict(
            gaps=(_gap(gap_id="G-1"), _gap(gap_id="G-2")),
            receipts=(big_a, big_b),
        )
        self.assertFalse(v.safe)
        self.assertTrue(
            any("lead context limit" in b for b in v.blockers),
        )

    def test_full_safe_verdict(self) -> None:
        v = _safe_verdict()
        self.assertTrue(v.safe)
        self.assertEqual(v.blockers, ())
        self.assertEqual(v.conflicts, ())

    def test_multiple_workers_all_gaps_covered(self) -> None:
        r_a = _receipt(worker_id="W-A", gaps=("G-1", "G-2"))
        r_b = _receipt(worker_id="W-B", gaps=("G-3",))
        gaps = (
            _gap(gap_id="G-1"),
            _gap(gap_id="G-2"),
            _gap(gap_id="G-3"),
        )
        v = _safe_verdict(gaps=gaps, receipts=(r_a, r_b))
        self.assertTrue(v.safe)

    def test_gap_type_enum_completeness(self) -> None:
        self.assertEqual(len(csg.GapType), 11)
        self.assertEqual(len(csg.VALID_GAP_TYPES), 11)

    def test_gap_status_enum_completeness(self) -> None:
        self.assertEqual(len(csg.GapStatus), 6)
        self.assertEqual(len(csg.VALID_GAP_STATUSES), 6)


if __name__ == "__main__":
    unittest.main()
