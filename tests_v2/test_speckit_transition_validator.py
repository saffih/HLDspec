"""Tests for the SpecKit transition validator (pure function, no execution)."""
from __future__ import annotations

import time
import unittest

from hldspec.speckit_transition_validator import (
    CANONICAL_PHASES,
    PhaseReceipt,
    TransitionRequest,
    ValidationResult,
    validate_speckit_transition,
)


TARGET = "my-project"
NOW = time.time()
FRESH = NOW - 10


def _receipt(phase: str, *, target: str = TARGET, created_at: float = FRESH,
             source_evidence_sha: str = "abc123") -> PhaseReceipt:
    return PhaseReceipt(
        target_id=target,
        source_evidence_sha=source_evidence_sha,
        phase=phase,
        created_at=created_at,
    )


def _request(from_phase: str, to_phase: str, *, target: str = TARGET,
             manual_fallback: bool = False) -> TransitionRequest:
    return TransitionRequest(
        target_id=target,
        from_phase=from_phase,
        to_phase=to_phase,
        manual_fallback=manual_fallback,
    )


def _validate(req: TransitionRequest, receipts: list[PhaseReceipt], *,
              speckit_available: bool = True, human_approval: bool = False,
              now: float = NOW) -> ValidationResult:
    return validate_speckit_transition(
        req, receipts,
        speckit_available=speckit_available,
        human_approval=human_approval,
        now=now,
    )


class SpecKitUnavailableTests(unittest.TestCase):
    def test_unavailable_blocks_without_fallback(self) -> None:
        req = _request("specify", "plan")
        result = _validate(req, [_receipt("specify")], speckit_available=False)
        self.assertEqual(result.status, "STOP_SKILL_UNAVAILABLE")

    def test_unavailable_blocks_even_with_all_receipts(self) -> None:
        req = _request("analyze", "implementation")
        receipts = [_receipt("specify"), _receipt("plan"),
                    _receipt("tasks"), _receipt("analyze")]
        result = _validate(req, receipts, speckit_available=False,
                           human_approval=True)
        self.assertEqual(result.status, "STOP_SKILL_UNAVAILABLE")


class ManualFallbackTests(unittest.TestCase):
    def test_manual_fallback_rejected(self) -> None:
        req = _request("specify", "plan", manual_fallback=True)
        result = _validate(req, [_receipt("specify")])
        self.assertEqual(result.status, "STOP_MANUAL_FALLBACK_FORBIDDEN")


class MissingReceiptTests(unittest.TestCase):
    def test_plan_without_specify_receipt(self) -> None:
        req = _request("specify", "plan")
        result = _validate(req, [])
        self.assertEqual(result.status, "STOP_MISSING_SPECIFY_RECEIPT")

    def test_tasks_without_plan_receipt(self) -> None:
        req = _request("plan", "tasks")
        result = _validate(req, [_receipt("specify")])
        self.assertEqual(result.status, "STOP_MISSING_PLAN_RECEIPT")

    def test_analyze_without_tasks_receipt(self) -> None:
        req = _request("tasks", "analyze")
        result = _validate(req, [_receipt("specify"), _receipt("plan")])
        self.assertEqual(result.status, "STOP_MISSING_TASKS_RECEIPT")

    def test_implementation_without_analyze_receipt(self) -> None:
        req = _request("analyze", "implementation")
        receipts = [_receipt("specify"), _receipt("plan"), _receipt("tasks")]
        result = _validate(req, receipts, human_approval=True)
        self.assertEqual(result.status, "STOP_MISSING_ANALYZE_RECEIPT")


class StaleReceiptTests(unittest.TestCase):
    def test_stale_receipt_rejected(self) -> None:
        req = _request("specify", "plan")
        stale = _receipt("specify", created_at=NOW - 90000)
        result = _validate(req, [stale])
        self.assertEqual(result.status, "STOP_STALE_RECEIPT")

    def test_fresh_receipt_accepted(self) -> None:
        req = _request("specify", "plan")
        result = _validate(req, [_receipt("specify")])
        self.assertEqual(result.status, "PASS")


class WrongTargetTests(unittest.TestCase):
    def test_wrong_target_receipt_rejected(self) -> None:
        req = _request("specify", "plan")
        wrong = _receipt("specify", target="other-project")
        result = _validate(req, [wrong])
        self.assertEqual(result.status, "STOP_WRONG_TARGET_RECEIPT")


class HumanApprovalTests(unittest.TestCase):
    def test_implementation_requires_human_approval(self) -> None:
        req = _request("analyze", "implementation")
        receipts = [_receipt("specify"), _receipt("plan"),
                    _receipt("tasks"), _receipt("analyze")]
        result = _validate(req, receipts, human_approval=False)
        self.assertEqual(result.status, "STOP_HUMAN_APPROVAL_REQUIRED")

    def test_implementation_passes_with_approval(self) -> None:
        req = _request("analyze", "implementation")
        receipts = [_receipt("specify"), _receipt("plan"),
                    _receipt("tasks"), _receipt("analyze")]
        result = _validate(req, receipts, human_approval=True)
        self.assertEqual(result.status, "PASS")


class CanonicalOrderTests(unittest.TestCase):
    def test_canonical_phases_match_contract(self) -> None:
        self.assertEqual(
            CANONICAL_PHASES,
            ("specify", "plan", "tasks", "analyze", "implementation"),
        )

    def test_skip_phase_rejected(self) -> None:
        req = _request("specify", "tasks")
        result = _validate(req, [_receipt("specify")])
        self.assertEqual(result.status, "STOP_CANONICAL_SEQUENCE_RECONCILIATION_REQUIRED")

    def test_backward_transition_rejected(self) -> None:
        req = _request("tasks", "specify")
        result = _validate(req, [_receipt("specify"), _receipt("plan"),
                                  _receipt("tasks")])
        self.assertEqual(result.status, "STOP_CANONICAL_SEQUENCE_RECONCILIATION_REQUIRED")


class HappyPathTests(unittest.TestCase):
    def test_specify_to_plan(self) -> None:
        result = _validate(_request("specify", "plan"), [_receipt("specify")])
        self.assertEqual(result.status, "PASS")

    def test_plan_to_tasks(self) -> None:
        result = _validate(
            _request("plan", "tasks"),
            [_receipt("specify"), _receipt("plan")],
        )
        self.assertEqual(result.status, "PASS")

    def test_tasks_to_analyze(self) -> None:
        result = _validate(
            _request("tasks", "analyze"),
            [_receipt("specify"), _receipt("plan"), _receipt("tasks")],
        )
        self.assertEqual(result.status, "PASS")

    def test_full_chain_to_implementation(self) -> None:
        receipts = [_receipt("specify"), _receipt("plan"),
                    _receipt("tasks"), _receipt("analyze")]
        result = _validate(
            _request("analyze", "implementation"), receipts,
            human_approval=True,
        )
        self.assertEqual(result.status, "PASS")


class NoSideEffectTests(unittest.TestCase):
    def test_validator_does_not_write_files(self) -> None:
        import hldspec.speckit_transition_validator as mod
        import inspect
        source = inspect.getsource(mod)
        for forbidden in ("open(", ".write(", "Path(", "mkdir", "os."):
            self.assertNotIn(forbidden, source,
                             f"validator must not contain '{forbidden}'")

    def test_validator_does_not_import_speckit(self) -> None:
        import hldspec.speckit_transition_validator as mod
        import inspect
        source = inspect.getsource(mod)
        for forbidden in ("speckit_invoker", "speckit_workspace",
                          "speckit_drive_loop"):
            self.assertNotIn(forbidden, source)


class ResultFieldTests(unittest.TestCase):
    def test_pass_result_has_reason(self) -> None:
        result = _validate(_request("specify", "plan"), [_receipt("specify")])
        self.assertEqual(result.status, "PASS")
        self.assertIsInstance(result.reason, str)
        self.assertTrue(len(result.reason) > 0)

    def test_stop_result_has_reason(self) -> None:
        result = _validate(_request("specify", "plan"), [])
        self.assertIn("STOP", result.status)
        self.assertIsInstance(result.reason, str)
        self.assertTrue(len(result.reason) > 0)


if __name__ == "__main__":
    unittest.main()
