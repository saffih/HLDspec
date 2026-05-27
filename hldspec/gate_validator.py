"""Gate validator — fail-closed checks for every HLDspec gate.

Encodes the gate names and the blocking conditions from the rewrite contract:
a gate blocks on a missing Context Receipt, missing source refs, failed
validation, stale anchors, unsupported claims, RunSkeptic ACTION/CONFLICT (or a
missing RunSkeptic PASS where required), a Consultant BLOCK (or a missing
Consultant PASS where required), and a missing human approval where required.

Allowed continuation = runner output + validation PASS + (where required)
RunSkeptic PASS + Consultant PASS + human approval.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Gate names
# ---------------------------------------------------------------------------
HLD_SHAPING_REVIEW_GATE = "HLD_SHAPING_REVIEW_GATE"
SOURCE_PACKAGE_APPROVAL_GATE = "SOURCE_PACKAGE_APPROVAL_GATE"
CONSTITUTION_APPROVAL_GATE = "CONSTITUTION_APPROVAL_GATE"
SPECKIT_SPECIFY_REVIEW_GATE = "SPECKIT_SPECIFY_REVIEW_GATE"
SPECKIT_PLAN_REVIEW_GATE = "SPECKIT_PLAN_REVIEW_GATE"
SPECKIT_TASKS_REVIEW_GATE = "SPECKIT_TASKS_REVIEW_GATE"
UI_VALIDATION_GATE = "UI_VALIDATION_GATE"
PRE_IMPLEMENTATION_APPROVAL_GATE = "PRE_IMPLEMENTATION_APPROVAL_GATE"
RELEASE_OR_PUSH_GATE = "RELEASE_OR_PUSH_GATE"

# Allowed RunSkeptic status words (terminology doc §6 + NOT_REQUIRED/NOT_RUN).
RUNSKEPTIC_PASS = "PASS"
RUNSKEPTIC_ACTION = "ACTION"
RUNSKEPTIC_CONFLICT = "CONFLICT"
RUNSKEPTIC_NOT_REQUIRED = "NOT_REQUIRED"
RUNSKEPTIC_NOT_RUN = "NOT_RUN"
VALID_RUNSKEPTIC_STATUSES = frozenset(
    {
        RUNSKEPTIC_PASS,
        RUNSKEPTIC_ACTION,
        RUNSKEPTIC_CONFLICT,
        RUNSKEPTIC_NOT_REQUIRED,
        RUNSKEPTIC_NOT_RUN,
    }
)

CONSULTANT_PASS = "PASS"
CONSULTANT_BLOCK = "BLOCK"
CONSULTANT_NOT_RUN = "NOT_RUN"
VALID_CONSULTANT_STATUSES = frozenset({CONSULTANT_PASS, CONSULTANT_BLOCK, CONSULTANT_NOT_RUN})


@dataclass(frozen=True)
class GateRequirements:
    requires_receipt: bool = True
    requires_source_refs: bool = True
    requires_runskeptic_pass: bool = False
    requires_consultant_pass: bool = False
    requires_human_approval: bool = False


# Per-gate requirements. Review/approval gates require human approval; gates that
# touch product truth require RunSkeptic + Consultant PASS.
GATE_REQUIREMENTS: dict[str, GateRequirements] = {
    HLD_SHAPING_REVIEW_GATE: GateRequirements(
        requires_runskeptic_pass=True, requires_human_approval=True
    ),
    SOURCE_PACKAGE_APPROVAL_GATE: GateRequirements(
        requires_runskeptic_pass=True,
        requires_consultant_pass=True,
        requires_human_approval=True,
    ),
    CONSTITUTION_APPROVAL_GATE: GateRequirements(
        requires_runskeptic_pass=True, requires_human_approval=True
    ),
    SPECKIT_SPECIFY_REVIEW_GATE: GateRequirements(requires_consultant_pass=True),
    SPECKIT_PLAN_REVIEW_GATE: GateRequirements(
        requires_runskeptic_pass=True, requires_consultant_pass=True
    ),
    SPECKIT_TASKS_REVIEW_GATE: GateRequirements(requires_consultant_pass=True),
    UI_VALIDATION_GATE: GateRequirements(requires_source_refs=False),
    PRE_IMPLEMENTATION_APPROVAL_GATE: GateRequirements(
        requires_runskeptic_pass=True,
        requires_consultant_pass=True,
        requires_human_approval=True,
    ),
    RELEASE_OR_PUSH_GATE: GateRequirements(
        requires_runskeptic_pass=True, requires_human_approval=True
    ),
}


@dataclass
class GateContext:
    receipt_present: bool = False
    source_refs: list[str] = field(default_factory=list)
    runskeptic_status: str = RUNSKEPTIC_NOT_RUN
    consultant_status: str = CONSULTANT_NOT_RUN
    unsupported_claims: list[str] = field(default_factory=list)
    stale_anchors: list[str] = field(default_factory=list)
    validation_ok: bool = True
    human_approved: bool = False


@dataclass
class GateResult:
    gate: str
    passed: bool
    blockers: list[str] = field(default_factory=list)


class UnknownGate(KeyError):
    pass


def validate_gate(gate: str, ctx: GateContext) -> GateResult:
    try:
        req = GATE_REQUIREMENTS[gate]
    except KeyError as exc:
        raise UnknownGate(f"unknown gate: {gate!r}") from exc

    blockers: list[str] = []

    if req.requires_receipt and not ctx.receipt_present:
        blockers.append("missing Context Receipt")

    if req.requires_source_refs and not ctx.source_refs:
        blockers.append("missing source anchors/refs")

    if not ctx.validation_ok:
        blockers.append("failed validation")

    if ctx.stale_anchors:
        blockers.append(f"stale anchors: {', '.join(ctx.stale_anchors)}")

    if ctx.unsupported_claims:
        blockers.append(f"unsupported claims: {', '.join(ctx.unsupported_claims)}")

    # RunSkeptic: an explicit ACTION/CONFLICT always blocks. Where PASS is
    # required, anything other than PASS/NOT_REQUIRED blocks.
    if ctx.runskeptic_status not in VALID_RUNSKEPTIC_STATUSES:
        blockers.append(f"invalid RunSkeptic status: {ctx.runskeptic_status!r}")
    elif ctx.runskeptic_status in {RUNSKEPTIC_ACTION, RUNSKEPTIC_CONFLICT}:
        blockers.append(f"RunSkeptic {ctx.runskeptic_status}")
    elif req.requires_runskeptic_pass and ctx.runskeptic_status not in {
        RUNSKEPTIC_PASS,
        RUNSKEPTIC_NOT_REQUIRED,
    }:
        blockers.append("missing RunSkeptic PASS")

    # Consultant: a BLOCK always blocks. Where PASS is required, NOT_RUN blocks.
    if ctx.consultant_status not in VALID_CONSULTANT_STATUSES:
        blockers.append(f"invalid Consultant status: {ctx.consultant_status!r}")
    elif ctx.consultant_status == CONSULTANT_BLOCK:
        blockers.append("Consultant BLOCK")
    elif req.requires_consultant_pass and ctx.consultant_status != CONSULTANT_PASS:
        blockers.append("missing Consultant PASS")

    if req.requires_human_approval and not ctx.human_approved:
        blockers.append("missing human approval")

    return GateResult(gate=gate, passed=not blockers, blockers=blockers)
