"""Journey 2 HLD Coverage Ledger contracts v0 -- pure validation helpers.

Journey 2 (`docs/JOURNEY2_SDD_COMPLETENESS_GATE.md`) tracks every HLD item
into the SDD/package via a typed coverage ledger. This module is the
deterministic, machine-checkable shape of those artifacts.

Intentionally minimal and side-effect free: pure functions over plain dicts
only -- NO filesystem reads/writes, NO target paths, NO subprocess, NO
SpecKit imports, NO CLI. Producing/populating these artifacts is future work.

Terminology aligns with `docs/JOURNEY2_SDD_COMPLETENESS_GATE.md` §4-§5.
Clarifications reference the inquiry ledger
(`docs/JOURNEY2_INQUIRY_LEDGER_CONTRACT.md`) by ID -- they do not duplicate
the OPEN/ESCALATED/ASSUMED/RESOLVED/DEFERRED lifecycle owned there.

Authority boundary: these contracts are evidence/completeness inputs only.
They grant no approval, implementation, work-order, or SpecKit authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# --- Item types (aligned with JOURNEY2_SDD_COMPLETENESS_GATE.md §5) --------

ITEM_REQUIREMENT = "REQUIREMENT"
ITEM_CONSTRAINT = "CONSTRAINT"
ITEM_COMPONENT = "COMPONENT"
ITEM_WORKFLOW = "WORKFLOW"
ITEM_NFR = "NFR"
ITEM_DATA_ITEM = "DATA_ITEM"
ITEM_API_CONTRACT = "API_CONTRACT"
ITEM_SECURITY_ITEM = "SECURITY_ITEM"
ITEM_INTEGRATION_POINT = "INTEGRATION_POINT"
ITEM_DEPLOYMENT_ITEM = "DEPLOYMENT_ITEM"
ITEM_OPERATIONAL_ITEM = "OPERATIONAL_ITEM"
ITEM_AMBIGUITY = "AMBIGUITY"
ITEM_OPEN_QUESTION = "OPEN_QUESTION"
ITEM_PRODUCT_DECISION = "PRODUCT_DECISION"

VALID_ITEM_TYPES: frozenset[str] = frozenset({
    ITEM_REQUIREMENT,
    ITEM_CONSTRAINT,
    ITEM_COMPONENT,
    ITEM_WORKFLOW,
    ITEM_NFR,
    ITEM_DATA_ITEM,
    ITEM_API_CONTRACT,
    ITEM_SECURITY_ITEM,
    ITEM_INTEGRATION_POINT,
    ITEM_DEPLOYMENT_ITEM,
    ITEM_OPERATIONAL_ITEM,
    ITEM_AMBIGUITY,
    ITEM_OPEN_QUESTION,
    ITEM_PRODUCT_DECISION,
})

# --- Coverage statuses (aligned with JOURNEY2_SDD_COMPLETENESS_GATE.md §5) -

STATUS_COVERED_IN_SDD = "COVERED_IN_SDD"
STATUS_NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
STATUS_BLOCKED_BY_PRODUCT_DECISION = "BLOCKED_BY_PRODUCT_DECISION"
STATUS_RESEARCH_REQUIRED = "RESEARCH_REQUIRED"
STATUS_OUT_OF_SCOPE = "OUT_OF_SCOPE_BY_EXPLICIT_DECISION"
STATUS_NOT_COVERED = "NOT_COVERED"

VALID_COVERAGE_STATUSES: frozenset[str] = frozenset({
    STATUS_COVERED_IN_SDD,
    STATUS_NEEDS_CLARIFICATION,
    STATUS_BLOCKED_BY_PRODUCT_DECISION,
    STATUS_RESEARCH_REQUIRED,
    STATUS_OUT_OF_SCOPE,
    STATUS_NOT_COVERED,
})

BLOCKING_STATUSES: frozenset[str] = frozenset({
    STATUS_NOT_COVERED,
})

EXPLICIT_STATUSES: frozenset[str] = frozenset({
    STATUS_NEEDS_CLARIFICATION,
    STATUS_RESEARCH_REQUIRED,
    STATUS_OUT_OF_SCOPE,
})

# --- Risk levels -------------------------------------------------------------

RISK_HIGH = "HIGH"
RISK_MEDIUM = "MEDIUM"
RISK_LOW = "LOW"

VALID_RISK_LEVELS: frozenset[str] = frozenset({RISK_HIGH, RISK_MEDIUM, RISK_LOW})

# --- Errors ------------------------------------------------------------------


class InvalidCoverageItemError(ValueError):
    """Raised on a structurally invalid coverage ledger item."""


# --- Validation helpers ------------------------------------------------------


def validate_item_type(item_type: Any) -> str:
    if item_type not in VALID_ITEM_TYPES:
        raise InvalidCoverageItemError(
            f"unknown item type: {item_type!r} (valid: {sorted(VALID_ITEM_TYPES)})"
        )
    return item_type


def validate_coverage_status(status: Any) -> str:
    if status not in VALID_COVERAGE_STATUSES:
        raise InvalidCoverageItemError(
            f"unknown coverage status: {status!r} (valid: {sorted(VALID_COVERAGE_STATUSES)})"
        )
    return status


def validate_risk_level(risk: Any) -> str:
    if risk not in VALID_RISK_LEVELS:
        raise InvalidCoverageItemError(
            f"unknown risk level: {risk!r} (valid: {sorted(VALID_RISK_LEVELS)})"
        )
    return risk


def validate_coverage_item(item: Any) -> dict[str, Any]:
    """Validate one HLD coverage ledger item dict.

    Enforces: known item_type, known status, hld_item_id present,
    source_section present, and status-specific constraints:
    - OUT_OF_SCOPE requires a non-empty assumption or design_decision.
    - RESEARCH_REQUIRED must have research_required=True.
    - NEEDS_CLARIFICATION must have clarification_required=True.
    """
    if not isinstance(item, dict):
        raise InvalidCoverageItemError("coverage item is not an object")

    hld_item_id = item.get("hld_item_id")
    if not hld_item_id or not isinstance(hld_item_id, str):
        raise InvalidCoverageItemError("coverage item has no hld_item_id")

    source_section = item.get("source_section")
    if not source_section or not isinstance(source_section, str):
        raise InvalidCoverageItemError("coverage item has no source_section")

    validate_item_type(item.get("item_type"))
    status = validate_coverage_status(item.get("status"))

    if "risk" in item and item["risk"] is not None:
        validate_risk_level(item["risk"])

    if status == STATUS_OUT_OF_SCOPE:
        assumption = (item.get("assumption") or "").strip()
        decision = (item.get("design_decision") or "").strip()
        if not assumption and not decision:
            raise InvalidCoverageItemError(
                f"OUT_OF_SCOPE_BY_EXPLICIT_DECISION requires an explicit "
                f"assumption or design_decision (item {hld_item_id!r})"
            )

    if status == STATUS_RESEARCH_REQUIRED:
        if not item.get("research_required"):
            raise InvalidCoverageItemError(
                f"RESEARCH_REQUIRED status must have research_required=True "
                f"(item {hld_item_id!r})"
            )

    if status == STATUS_NEEDS_CLARIFICATION:
        if not item.get("clarification_required"):
            raise InvalidCoverageItemError(
                f"NEEDS_CLARIFICATION status must have "
                f"clarification_required=True (item {hld_item_id!r})"
            )

    return item


# --- Artifact containers -----------------------------------------------------


def validate_requirement_inventory(inventory: Any) -> list[dict[str, Any]]:
    """Validate an HldRequirementInventory (list of HLD items).

    Each item must have hld_item_id, source_section, item_type.
    """
    if not isinstance(inventory, list):
        raise InvalidCoverageItemError("requirement inventory is not a list")
    validated: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for entry in inventory:
        if not isinstance(entry, dict):
            raise InvalidCoverageItemError("inventory entry is not an object")
        hld_item_id = entry.get("hld_item_id")
        if not hld_item_id or not isinstance(hld_item_id, str):
            raise InvalidCoverageItemError("inventory entry has no hld_item_id")
        if hld_item_id in seen_ids:
            raise InvalidCoverageItemError(
                f"duplicate hld_item_id in inventory: {hld_item_id!r}"
            )
        seen_ids.add(hld_item_id)
        validate_item_type(entry.get("item_type"))
        source_section = entry.get("source_section")
        if not source_section or not isinstance(source_section, str):
            raise InvalidCoverageItemError("inventory entry has no source_section")
        validated.append(entry)
    return validated


def validate_coverage_ledger(ledger: Any) -> list[dict[str, Any]]:
    """Validate an HldCoverageLedger (list of coverage items)."""
    if not isinstance(ledger, list):
        raise InvalidCoverageItemError("coverage ledger is not a list")
    return [validate_coverage_item(item) for item in ledger]


def incomplete_items(ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return items that are not terminally covered.

    Terminal statuses: COVERED_IN_SDD, OUT_OF_SCOPE_BY_EXPLICIT_DECISION.
    Everything else is incomplete and blocks full completeness.
    """
    terminal = frozenset({STATUS_COVERED_IN_SDD, STATUS_OUT_OF_SCOPE})
    return [item for item in ledger if item.get("status") not in terminal]


def blocking_items(ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return items with blocking statuses (NOT_COVERED)."""
    return [item for item in ledger if item.get("status") in BLOCKING_STATUSES]


def needs_clarification_items(ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return items needing clarification."""
    return [
        item for item in ledger if item.get("status") == STATUS_NEEDS_CLARIFICATION
    ]


def research_required_items(ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return items needing research."""
    return [
        item for item in ledger if item.get("status") == STATUS_RESEARCH_REQUIRED
    ]


# --- SDD section coverage map ------------------------------------------------


def build_sdd_section_coverage_map(
    ledger: list[dict[str, Any]],
) -> dict[str, list[str]]:
    """Build a reverse map: SDD section -> list of hld_item_ids it covers.

    Items without an sdd_section are omitted (they have no SDD grounding).
    """
    section_map: dict[str, list[str]] = {}
    for item in ledger:
        sdd_section = item.get("sdd_section")
        if not sdd_section:
            continue
        sections = sdd_section if isinstance(sdd_section, list) else [sdd_section]
        for section in sections:
            section_map.setdefault(section, []).append(item["hld_item_id"])
    return section_map


def unlinked_sdd_sections(
    sdd_sections: list[str],
    ledger: list[dict[str, Any]],
) -> list[str]:
    """Return SDD sections with no HLD grounding (potential invented content)."""
    covered = build_sdd_section_coverage_map(ledger)
    return [s for s in sdd_sections if s not in covered]


# --- Completeness report -----------------------------------------------------


@dataclass(frozen=True)
class SddCompletenessReport:
    """The final gate artifact for SDD completeness."""

    all_items_inventoried: bool
    all_covered: bool
    total_items: int
    covered_count: int
    not_covered_count: int
    needs_clarification_count: int
    research_required_count: int
    blocked_by_product_decision_count: int
    out_of_scope_count: int
    incomplete_items: list[dict[str, Any]] = field(default_factory=list)
    unlinked_sections: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "all_items_inventoried": self.all_items_inventoried,
            "all_covered": self.all_covered,
            "total_items": self.total_items,
            "covered_count": self.covered_count,
            "not_covered_count": self.not_covered_count,
            "needs_clarification_count": self.needs_clarification_count,
            "research_required_count": self.research_required_count,
            "blocked_by_product_decision_count": self.blocked_by_product_decision_count,
            "out_of_scope_count": self.out_of_scope_count,
            "incomplete_item_ids": [i["hld_item_id"] for i in self.incomplete_items],
            "unlinked_sections": self.unlinked_sections,
        }


def build_completeness_report(
    inventory: list[dict[str, Any]],
    ledger: list[dict[str, Any]],
    sdd_sections: list[str] | None = None,
) -> SddCompletenessReport:
    """Build an SddCompletenessReport from inventory + ledger.

    Does not mutate inputs. Pure computation only.
    """
    validated_ledger = validate_coverage_ledger(ledger)
    ledger_ids = {item["hld_item_id"] for item in validated_ledger}
    inventory_ids = {item["hld_item_id"] for item in inventory}
    all_inventoried = inventory_ids <= ledger_ids

    by_status: dict[str, int] = {}
    for item in validated_ledger:
        s = item["status"]
        by_status[s] = by_status.get(s, 0) + 1

    inc = incomplete_items(validated_ledger)
    unlinked = unlinked_sdd_sections(sdd_sections or [], validated_ledger)

    return SddCompletenessReport(
        all_items_inventoried=all_inventoried,
        all_covered=len(inc) == 0,
        total_items=len(validated_ledger),
        covered_count=by_status.get(STATUS_COVERED_IN_SDD, 0),
        not_covered_count=by_status.get(STATUS_NOT_COVERED, 0),
        needs_clarification_count=by_status.get(STATUS_NEEDS_CLARIFICATION, 0),
        research_required_count=by_status.get(STATUS_RESEARCH_REQUIRED, 0),
        blocked_by_product_decision_count=by_status.get(
            STATUS_BLOCKED_BY_PRODUCT_DECISION, 0
        ),
        out_of_scope_count=by_status.get(STATUS_OUT_OF_SCOPE, 0),
        incomplete_items=inc,
        unlinked_sections=unlinked,
    )


# --- Authority boundary (mirrors journey0_artifact_contracts pattern) --------

FORBIDDEN_ACTIONS: tuple[str, ...] = (
    "approve product decisions",
    "grant approval authority",
    "authorize implementation",
    "produce implementation work orders",
    "invoke SpecKit",
    "mutate target repos",
    "generate SDD content",
    "execute research",
)


def journey2_coverage_authority_profile() -> dict[str, Any]:
    """Authority boundary for coverage contracts. Every grant is False.

    Coverage contracts are evidence/completeness inputs only. They never
    approve, never authorize implementation or work orders, never invoke
    SpecKit, and never generate SDD content.
    """
    return {
        "grants_approval_authority": False,
        "authorizes_implementation": False,
        "authorizes_work_orders": False,
        "invokes_speckit": False,
        "generates_sdd": False,
        "executes_research": False,
        "mutates_target": False,
        "forbidden_actions": list(FORBIDDEN_ACTIONS),
    }
