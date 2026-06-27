"""Journey 0 Brownfield Discovery artifact contracts v0 -- pure validation helpers.

Journey 0 (`docs/JOURNEY0_BROWNFIELD_DISCOVERY.md`) is the read-only PRE-HLD
on-ramp for brownfield products: it inspects existing evidence, classifies gaps
and conflicts, and decides whether an authoritative HLD can responsibly be
written -- then hands off to Journey 1 as *evidence and gap input only*.

This module is the deterministic, machine-checkable shape of Journey 0's
artifacts and authority boundary. It is intentionally minimal and side-effect
free: pure functions over plain dicts only -- NO filesystem reads/writes, NO
target paths, NO subprocess, NO SpecKit imports, NO CLI. It contains no scanner
or repo-discovery logic; producing the artifacts it validates is future work.

Load-bearing product rules encoded here:

- Evidence carries a constrained label (`VALID_EVIDENCE_LABELS`); an unknown
  label raises rather than passing silently.
- A `CONFLICT` cannot silently become an accepted fact -- only `OBSERVED`
  evidence is an accepted fact, and `promote_to_accepted_fact` refuses anything
  else.
- Open product decisions block HLD draftability
  (`assess_hld_draftability` -> `BLOCKED_PRODUCT_DECISIONS_REQUIRED`).
- Journey 0 artifacts grant NO approval authority and authorize NO
  implementation / work orders (`journey0_authority_profile`, all False); the
  Journey 1 handoff is evidence/gap input only.
"""
from __future__ import annotations

from typing import Any

# --- Evidence labels --------------------------------------------------------

EVIDENCE_OBSERVED = "OBSERVED"
EVIDENCE_INFERRED = "INFERRED"
EVIDENCE_UNKNOWN = "UNKNOWN"
EVIDENCE_CONFLICT = "CONFLICT"
EVIDENCE_PRODUCT_DECISION_REQUIRED = "PRODUCT_DECISION_REQUIRED"

VALID_EVIDENCE_LABELS: frozenset[str] = frozenset(
    {
        EVIDENCE_OBSERVED,
        EVIDENCE_INFERRED,
        EVIDENCE_UNKNOWN,
        EVIDENCE_CONFLICT,
        EVIDENCE_PRODUCT_DECISION_REQUIRED,
    }
)

# --- HLD draftability verdicts ----------------------------------------------

VERDICT_READY_TO_DRAFT_HLD = "READY_TO_DRAFT_HLD"
VERDICT_READY_WITH_OPEN_QUESTIONS = "READY_WITH_OPEN_QUESTIONS"
VERDICT_BLOCKED_PRODUCT_DECISIONS_REQUIRED = "BLOCKED_PRODUCT_DECISIONS_REQUIRED"
VERDICT_BLOCKED_REPO_STATE_CONFLICT = "BLOCKED_REPO_STATE_CONFLICT"
VERDICT_INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

VALID_DRAFTABILITY_VERDICTS: frozenset[str] = frozenset(
    {
        VERDICT_READY_TO_DRAFT_HLD,
        VERDICT_READY_WITH_OPEN_QUESTIONS,
        VERDICT_BLOCKED_PRODUCT_DECISIONS_REQUIRED,
        VERDICT_BLOCKED_REPO_STATE_CONFLICT,
        VERDICT_INSUFFICIENT_EVIDENCE,
    }
)

# Only these verdicts permit proceeding to Journey 1's HLD authoring/hardening.
DRAFTABLE_VERDICTS: frozenset[str] = frozenset(
    {VERDICT_READY_TO_DRAFT_HLD, VERDICT_READY_WITH_OPEN_QUESTIONS}
)

# --- Artifact kinds (the seven Journey 0 outputs) ---------------------------

ARTIFACT_BROWNFIELD_EVIDENCE_PACK = "BrownfieldEvidencePack"
ARTIFACT_PRODUCT_SURFACE_MAP = "ProductSurfaceMap"
ARTIFACT_SPEC_INVENTORY = "SpecInventory"
ARTIFACT_HLD_GAP_REPORT = "HLDGapReport"
ARTIFACT_PRODUCT_DECISION_REGISTER = "ProductDecisionRegister"
ARTIFACT_HLD_DRAFTABILITY_VERDICT = "HLDDraftabilityVerdict"
ARTIFACT_HLD_UPDATE_PLAN = "HLDUpdatePlan"

VALID_JOURNEY0_ARTIFACTS: frozenset[str] = frozenset(
    {
        ARTIFACT_BROWNFIELD_EVIDENCE_PACK,
        ARTIFACT_PRODUCT_SURFACE_MAP,
        ARTIFACT_SPEC_INVENTORY,
        ARTIFACT_HLD_GAP_REPORT,
        ARTIFACT_PRODUCT_DECISION_REGISTER,
        ARTIFACT_HLD_DRAFTABILITY_VERDICT,
        ARTIFACT_HLD_UPDATE_PLAN,
    }
)

# --- Authority boundary -----------------------------------------------------

# The only handoff Journey 0 may produce: evidence/gap input into Journey 1.
HANDOFF_EVIDENCE_AND_GAP_INPUT = "evidence_and_gap_input"

# Owner-only actions Journey 0 never performs and never authorizes. Always
# listed, never granted -- mirrors toolchain_driver's FORBIDDEN_ACTIONS pattern.
FORBIDDEN_ACTIONS: tuple[str, ...] = (
    "mutate the target repo",
    "create or modify .specify/",
    "create or modify target .hldspec/",
    "invoke SpecKit",
    "approve protected transitions",
    "produce implementation work orders",
    "grant approval authority",
    "authorize implementation",
    "silently resolve product or authority conflicts",
    "lift the arbitrary brownfield adoption restriction",
)


class InvalidJourney0ArtifactError(ValueError):
    """Raised on a structurally invalid Journey 0 artifact or label."""


# --- Evidence -----------------------------------------------------------------


def validate_evidence_label(label: Any) -> str:
    """Return `label` if it is a known evidence label; else raise.

    Constrains the label to `VALID_EVIDENCE_LABELS` so an unknown classification
    cannot pass silently into downstream gap routing or a handoff.
    """
    if label not in VALID_EVIDENCE_LABELS:
        raise InvalidJourney0ArtifactError(
            f"unknown evidence label: {label!r} (valid: {sorted(VALID_EVIDENCE_LABELS)})"
        )
    return label


def validate_evidence_item(item: Any) -> dict[str, Any]:
    """Validate one evidence item dict (must carry a constrained `label`)."""
    if not isinstance(item, dict):
        raise InvalidJourney0ArtifactError("evidence item is not an object")
    validate_evidence_label(item.get("label"))
    return item


def evidence_items(evidence_pack: Any) -> list[dict[str, Any]]:
    """Return the list of evidence items from a BrownfieldEvidencePack dict."""
    if not isinstance(evidence_pack, dict):
        raise InvalidJourney0ArtifactError("evidence pack is not an object")
    items = evidence_pack.get("evidence")
    if not isinstance(items, list):
        raise InvalidJourney0ArtifactError("evidence pack has no 'evidence' list")
    return [validate_evidence_item(item) for item in items]


def accepted_facts(evidence_pack: Any) -> list[dict[str, Any]]:
    """Return only OBSERVED items. CONFLICT/UNKNOWN/INFERRED/decision-required
    evidence is never an accepted fact -- it must be resolved first."""
    return [i for i in evidence_items(evidence_pack) if i.get("label") == EVIDENCE_OBSERVED]


def promote_to_accepted_fact(item: Any) -> dict[str, Any]:
    """Promote one evidence item to an accepted fact, or raise.

    Load-bearing invariant: a CONFLICT (or any non-OBSERVED label) can never
    silently become an accepted fact.
    """
    item = validate_evidence_item(item)
    if item.get("label") != EVIDENCE_OBSERVED:
        raise InvalidJourney0ArtifactError(
            f"cannot accept {item.get('label')!r} evidence as a fact; only "
            f"{EVIDENCE_OBSERVED} is an accepted fact (resolve it first)"
        )
    return item


# --- Product decisions --------------------------------------------------------


def open_product_decisions(decision_register: Any) -> list[dict[str, Any]]:
    """Return the unresolved entries of a ProductDecisionRegister.

    An entry is open when its `status` is anything other than "RESOLVED" (a
    missing/`OPEN`/`PRODUCT_DECISION_REQUIRED` status all count as open).
    """
    if decision_register is None:
        return []
    if not isinstance(decision_register, list):
        raise InvalidJourney0ArtifactError("product decision register is not a list")
    open_entries: list[dict[str, Any]] = []
    for entry in decision_register:
        if not isinstance(entry, dict):
            raise InvalidJourney0ArtifactError("decision register entry is not an object")
        if entry.get("status") != "RESOLVED":
            open_entries.append(entry)
    return open_entries


# --- HLD draftability ---------------------------------------------------------


def is_draftable(verdict: Any) -> bool:
    """True only for the two proceed-to-Journey-1 verdicts; raise on unknown."""
    if verdict not in VALID_DRAFTABILITY_VERDICTS:
        raise InvalidJourney0ArtifactError(
            f"unknown draftability verdict: {verdict!r} "
            f"(valid: {sorted(VALID_DRAFTABILITY_VERDICTS)})"
        )
    return verdict in DRAFTABLE_VERDICTS


def assess_hld_draftability(
    evidence_pack: Any,
    decision_register: Any,
    gap_report: Any,
) -> dict[str, Any]:
    """Map Journey 0 evidence/decisions/gaps to an HLD draftability verdict.

    Thin, deterministic precedence over simple typed inputs (no repo scanning):

    1. open product decisions      -> BLOCKED_PRODUCT_DECISIONS_REQUIRED
    2. repo-state conflict flagged  -> BLOCKED_REPO_STATE_CONFLICT
    3. no OBSERVED accepted facts   -> INSUFFICIENT_EVIDENCE
    4. any UNKNOWN open question    -> READY_WITH_OPEN_QUESTIONS
    5. otherwise                    -> READY_TO_DRAFT_HLD

    `gap_report` is opaque-but-required: a dict that may carry a typed
    `repo_state_conflict` boolean. Its conflict signal is a declared input, not
    derived by scanning evidence.
    """
    if not isinstance(gap_report, dict):
        raise InvalidJourney0ArtifactError("gap report is not an object")

    items = evidence_items(evidence_pack)
    open_decisions = open_product_decisions(decision_register)
    repo_state_conflict = bool(gap_report.get("repo_state_conflict"))
    has_accepted_fact = any(i.get("label") == EVIDENCE_OBSERVED for i in items)
    open_questions = [i for i in items if i.get("label") == EVIDENCE_UNKNOWN]

    if open_decisions:
        verdict = VERDICT_BLOCKED_PRODUCT_DECISIONS_REQUIRED
    elif repo_state_conflict:
        verdict = VERDICT_BLOCKED_REPO_STATE_CONFLICT
    elif not has_accepted_fact:
        verdict = VERDICT_INSUFFICIENT_EVIDENCE
    elif open_questions:
        verdict = VERDICT_READY_WITH_OPEN_QUESTIONS
    else:
        verdict = VERDICT_READY_TO_DRAFT_HLD

    return {
        "kind": ARTIFACT_HLD_DRAFTABILITY_VERDICT,
        "verdict": verdict,
        "draftable": is_draftable(verdict),
        "open_product_decisions": len(open_decisions),
        "repo_state_conflict": repo_state_conflict,
        "accepted_fact_count": sum(
            1 for i in items if i.get("label") == EVIDENCE_OBSERVED
        ),
        "open_question_count": len(open_questions),
    }


# --- Authority profile + Journey 1 handoff ------------------------------------


def journey0_authority_profile() -> dict[str, Any]:
    """The Journey 0 authority boundary. Every grant is a hardcoded False.

    Load-bearing invariant: Journey 0 is read-only assessment. It never approves,
    never authorizes implementation or work orders, never mutates a target,
    never invokes SpecKit, and does not lift the brownfield-adoption restriction.
    """
    return {
        # Never, in any mode -- Journey 0 only assesses and reports.
        "grants_approval_authority": False,
        "authorizes_implementation": False,
        "authorizes_work_orders": False,
        "mutates_target": False,
        "invokes_speckit": False,
        "resolves_conflicts_silently": False,
        "lifts_brownfield_adoption_restriction": False,
        "forbidden_actions": list(FORBIDDEN_ACTIONS),
    }


def validate_artifact(artifact: Any) -> dict[str, Any]:
    """Validate that an object declares a known Journey 0 artifact `kind`.

    Gives all seven Journey 0 outputs a typed identity without imposing a
    per-artifact field schema (that, and the scanner that would populate them,
    are future work).
    """
    if not isinstance(artifact, dict):
        raise InvalidJourney0ArtifactError("artifact is not an object")
    kind = artifact.get("kind")
    if kind not in VALID_JOURNEY0_ARTIFACTS:
        raise InvalidJourney0ArtifactError(
            f"unknown Journey 0 artifact kind: {kind!r} "
            f"(valid: {sorted(VALID_JOURNEY0_ARTIFACTS)})"
        )
    return artifact


def build_journey1_handoff(
    evidence_pack: Any,
    gap_report: Any,
    decision_register: Any,
) -> dict[str, Any]:
    """Build the Journey 0 -> Journey 1 handoff: evidence and gap input ONLY.

    The handoff carries evidence, gaps, accepted facts, and open product
    decisions for Journey 1 to author/harden an HLD from. It carries the Journey 0
    authority profile (all False) and NO approval, work-order, or implementation
    authorization. `handoff_kind` is fixed to `HANDOFF_EVIDENCE_AND_GAP_INPUT`.
    """
    if not isinstance(gap_report, dict):
        raise InvalidJourney0ArtifactError("gap report is not an object")
    items = evidence_items(evidence_pack)
    return {
        "handoff_kind": HANDOFF_EVIDENCE_AND_GAP_INPUT,
        "to_journey": "journey1",
        "evidence": items,
        "accepted_facts": [i for i in items if i.get("label") == EVIDENCE_OBSERVED],
        "gaps": gap_report,
        "open_product_decisions": open_product_decisions(decision_register),
        "draftability": assess_hld_draftability(evidence_pack, decision_register, gap_report),
        "authority": journey0_authority_profile(),
    }
