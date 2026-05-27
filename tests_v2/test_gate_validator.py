import unittest

from hldspec import gate_validator as gv


def _full_pass_ctx() -> gv.GateContext:
    return gv.GateContext(
        receipt_present=True,
        source_refs=["a:intro"],
        runskeptic_status=gv.RUNSKEPTIC_PASS,
        consultant_status=gv.CONSULTANT_PASS,
        validation_ok=True,
        human_approved=True,
    )


class GateRegistryTests(unittest.TestCase):
    def test_all_required_gates_defined(self):
        for gate in (
            gv.HLD_SHAPING_REVIEW_GATE,
            gv.SOURCE_PACKAGE_APPROVAL_GATE,
            gv.CONSTITUTION_APPROVAL_GATE,
            gv.SPECKIT_SPECIFY_REVIEW_GATE,
            gv.SPECKIT_PLAN_REVIEW_GATE,
            gv.SPECKIT_TASKS_REVIEW_GATE,
            gv.UI_VALIDATION_GATE,
            gv.PRE_IMPLEMENTATION_APPROVAL_GATE,
            gv.RELEASE_OR_PUSH_GATE,
        ):
            self.assertIn(gate, gv.GATE_REQUIREMENTS)

    def test_unknown_gate_raises(self):
        with self.assertRaises(gv.UnknownGate):
            gv.validate_gate("NOPE_GATE", _full_pass_ctx())


class GateBlockingTests(unittest.TestCase):
    def test_full_pass(self):
        result = gv.validate_gate(gv.SOURCE_PACKAGE_APPROVAL_GATE, _full_pass_ctx())
        self.assertTrue(result.passed, msg=result.blockers)

    def test_missing_receipt_blocks(self):
        ctx = _full_pass_ctx()
        ctx.receipt_present = False
        result = gv.validate_gate(gv.SOURCE_PACKAGE_APPROVAL_GATE, ctx)
        self.assertFalse(result.passed)
        self.assertIn("missing Context Receipt", result.blockers)

    def test_missing_source_refs_blocks(self):
        ctx = _full_pass_ctx()
        ctx.source_refs = []
        result = gv.validate_gate(gv.SOURCE_PACKAGE_APPROVAL_GATE, ctx)
        self.assertFalse(result.passed)
        self.assertIn("missing source anchors/refs", result.blockers)

    def test_failed_validation_blocks(self):
        ctx = _full_pass_ctx()
        ctx.validation_ok = False
        result = gv.validate_gate(gv.SOURCE_PACKAGE_APPROVAL_GATE, ctx)
        self.assertIn("failed validation", result.blockers)

    def test_stale_anchors_block(self):
        ctx = _full_pass_ctx()
        ctx.stale_anchors = ["a:gone"]
        result = gv.validate_gate(gv.SOURCE_PACKAGE_APPROVAL_GATE, ctx)
        self.assertFalse(result.passed)
        self.assertTrue(any("stale anchors" in b for b in result.blockers))

    def test_unsupported_claims_block(self):
        ctx = _full_pass_ctx()
        ctx.unsupported_claims = ["claim X has no anchor"]
        result = gv.validate_gate(gv.SOURCE_PACKAGE_APPROVAL_GATE, ctx)
        self.assertFalse(result.passed)
        self.assertTrue(any("unsupported claims" in b for b in result.blockers))

    def test_runskeptic_action_blocks_even_when_not_required(self):
        # SPECKIT_TASKS gate does not require RunSkeptic PASS, but an explicit
        # ACTION must still block.
        ctx = _full_pass_ctx()
        ctx.runskeptic_status = gv.RUNSKEPTIC_ACTION
        result = gv.validate_gate(gv.SPECKIT_TASKS_REVIEW_GATE, ctx)
        self.assertFalse(result.passed)
        self.assertIn("RunSkeptic ACTION", result.blockers)

    def test_runskeptic_conflict_blocks(self):
        ctx = _full_pass_ctx()
        ctx.runskeptic_status = gv.RUNSKEPTIC_CONFLICT
        result = gv.validate_gate(gv.PRE_IMPLEMENTATION_APPROVAL_GATE, ctx)
        self.assertIn("RunSkeptic CONFLICT", result.blockers)

    def test_missing_runskeptic_pass_blocks_when_required(self):
        ctx = _full_pass_ctx()
        ctx.runskeptic_status = gv.RUNSKEPTIC_NOT_RUN
        result = gv.validate_gate(gv.SOURCE_PACKAGE_APPROVAL_GATE, ctx)
        self.assertIn("missing RunSkeptic PASS", result.blockers)

    def test_not_required_runskeptic_allowed(self):
        ctx = _full_pass_ctx()
        ctx.runskeptic_status = gv.RUNSKEPTIC_NOT_REQUIRED
        result = gv.validate_gate(gv.SPECKIT_SPECIFY_REVIEW_GATE, ctx)
        self.assertTrue(result.passed, msg=result.blockers)

    def test_invalid_runskeptic_status_blocks(self):
        ctx = _full_pass_ctx()
        ctx.runskeptic_status = "GREEN"
        result = gv.validate_gate(gv.SPECKIT_SPECIFY_REVIEW_GATE, ctx)
        self.assertTrue(any("invalid RunSkeptic status" in b for b in result.blockers))

    def test_consultant_block_blocks(self):
        ctx = _full_pass_ctx()
        ctx.consultant_status = gv.CONSULTANT_BLOCK
        result = gv.validate_gate(gv.SPECKIT_SPECIFY_REVIEW_GATE, ctx)
        self.assertFalse(result.passed)
        self.assertIn("Consultant BLOCK", result.blockers)

    def test_missing_consultant_pass_blocks_when_required(self):
        ctx = _full_pass_ctx()
        ctx.consultant_status = gv.CONSULTANT_NOT_RUN
        result = gv.validate_gate(gv.SPECKIT_PLAN_REVIEW_GATE, ctx)
        self.assertIn("missing Consultant PASS", result.blockers)

    def test_missing_human_approval_blocks(self):
        ctx = _full_pass_ctx()
        ctx.human_approved = False
        result = gv.validate_gate(gv.PRE_IMPLEMENTATION_APPROVAL_GATE, ctx)
        self.assertIn("missing human approval", result.blockers)

    def test_ui_gate_does_not_require_source_refs(self):
        ctx = gv.GateContext(
            receipt_present=True,
            runskeptic_status=gv.RUNSKEPTIC_PASS,
            consultant_status=gv.CONSULTANT_PASS,
        )
        result = gv.validate_gate(gv.UI_VALIDATION_GATE, ctx)
        self.assertTrue(result.passed, msg=result.blockers)


if __name__ == "__main__":
    unittest.main()
