"""Contract tests for Journey 0 brownfield-discovery artifacts.

Pins the load-bearing product rules of docs/JOURNEY0_BROWNFIELD_DISCOVERY.md:
evidence labels are constrained, conflicts can never silently become accepted
facts, open product decisions block HLD draftability, and Journey 0 grants no
approval/implementation authority -- it hands to Journey 1 as evidence/gap input
only.
"""
from __future__ import annotations

import unittest

from hldspec import journey0_artifact_contracts as j0


def _evidence_pack(*labels: str) -> dict:
    return {
        "kind": j0.ARTIFACT_BROWNFIELD_EVIDENCE_PACK,
        "evidence": [
            {"label": label, "statement": f"evidence #{i} ({label})"}
            for i, label in enumerate(labels)
        ],
    }


def _gap_report(repo_state_conflict: bool = False) -> dict:
    return {"kind": j0.ARTIFACT_HLD_GAP_REPORT, "repo_state_conflict": repo_state_conflict}


def _decision_register(*statuses: str) -> list:
    return [{"id": f"PD-{i}", "status": s} for i, s in enumerate(statuses)]


class Journey0ArtifactContractsTests(unittest.TestCase):
    # 1. Evidence labels are constrained to the five Journey 0 labels.
    def test_evidence_labels_are_constrained(self) -> None:
        for label in (
            j0.EVIDENCE_OBSERVED,
            j0.EVIDENCE_INFERRED,
            j0.EVIDENCE_UNKNOWN,
            j0.EVIDENCE_CONFLICT,
            j0.EVIDENCE_PRODUCT_DECISION_REQUIRED,
        ):
            self.assertEqual(j0.validate_evidence_label(label), label)
        self.assertEqual(len(j0.VALID_EVIDENCE_LABELS), 5)
        with self.assertRaises(j0.InvalidJourney0ArtifactError):
            j0.validate_evidence_label("DEFINITELY")
        with self.assertRaises(j0.InvalidJourney0ArtifactError):
            j0.validate_evidence_item({"statement": "no label"})

    # 2. All seven artifacts have a constrained typed kind.
    def test_artifact_kinds_are_constrained(self) -> None:
        self.assertEqual(len(j0.VALID_JOURNEY0_ARTIFACTS), 7)
        for kind in j0.VALID_JOURNEY0_ARTIFACTS:
            self.assertEqual(j0.validate_artifact({"kind": kind})["kind"], kind)
        with self.assertRaises(j0.InvalidJourney0ArtifactError):
            j0.validate_artifact({"kind": "NotAJourney0Artifact"})

    # 3. A CONFLICT (or any non-OBSERVED label) can never silently become a fact.
    def test_conflict_cannot_become_accepted_fact(self) -> None:
        conflict_item = {"label": j0.EVIDENCE_CONFLICT, "statement": "two specs disagree"}
        with self.assertRaises(j0.InvalidJourney0ArtifactError):
            j0.promote_to_accepted_fact(conflict_item)
        # accepted_facts returns only OBSERVED items; CONFLICT/UNKNOWN are excluded.
        pack = _evidence_pack(
            j0.EVIDENCE_OBSERVED, j0.EVIDENCE_CONFLICT, j0.EVIDENCE_UNKNOWN
        )
        facts = j0.accepted_facts(pack)
        self.assertEqual(len(facts), 1)
        self.assertTrue(all(f["label"] == j0.EVIDENCE_OBSERVED for f in facts))

    # 4. Open product decisions block HLD draftability, even with sufficient evidence.
    def test_open_product_decisions_block_draftability(self) -> None:
        result = j0.assess_hld_draftability(
            _evidence_pack(j0.EVIDENCE_OBSERVED, j0.EVIDENCE_OBSERVED),
            _decision_register("OPEN"),  # one unresolved decision
            _gap_report(repo_state_conflict=False),
        )
        self.assertEqual(result["verdict"], j0.VERDICT_BLOCKED_PRODUCT_DECISIONS_REQUIRED)
        self.assertFalse(result["draftable"])
        self.assertFalse(j0.is_draftable(result["verdict"]))

    # 5a. Verdict: clean evidence, no decisions/conflict/questions -> ready.
    def test_verdict_ready_to_draft_hld(self) -> None:
        result = j0.assess_hld_draftability(
            _evidence_pack(j0.EVIDENCE_OBSERVED),
            _decision_register("RESOLVED"),
            _gap_report(),
        )
        self.assertEqual(result["verdict"], j0.VERDICT_READY_TO_DRAFT_HLD)
        self.assertTrue(result["draftable"])

    # 5b. Verdict: facts present but an open UNKNOWN -> ready with open questions.
    def test_verdict_ready_with_open_questions(self) -> None:
        result = j0.assess_hld_draftability(
            _evidence_pack(j0.EVIDENCE_OBSERVED, j0.EVIDENCE_UNKNOWN),
            None,
            _gap_report(),
        )
        self.assertEqual(result["verdict"], j0.VERDICT_READY_WITH_OPEN_QUESTIONS)
        self.assertTrue(result["draftable"])

    # 5c. Verdict: repo-state conflict flagged (no open decisions) -> blocked.
    def test_verdict_blocked_repo_state_conflict(self) -> None:
        result = j0.assess_hld_draftability(
            _evidence_pack(j0.EVIDENCE_OBSERVED),
            _decision_register("RESOLVED"),
            _gap_report(repo_state_conflict=True),
        )
        self.assertEqual(result["verdict"], j0.VERDICT_BLOCKED_REPO_STATE_CONFLICT)
        self.assertFalse(result["draftable"])

    # 5d. Verdict: no OBSERVED accepted fact -> insufficient evidence.
    def test_verdict_insufficient_evidence(self) -> None:
        result = j0.assess_hld_draftability(
            _evidence_pack(j0.EVIDENCE_INFERRED, j0.EVIDENCE_UNKNOWN),
            None,
            _gap_report(),
        )
        self.assertEqual(result["verdict"], j0.VERDICT_INSUFFICIENT_EVIDENCE)
        self.assertFalse(result["draftable"])

    def test_unknown_verdict_raises(self) -> None:
        self.assertEqual(len(j0.VALID_DRAFTABILITY_VERDICTS), 5)
        with self.assertRaises(j0.InvalidJourney0ArtifactError):
            j0.is_draftable("MAYBE")

    # 6. Journey 0 artifacts grant NO approval authority (negative space, not a
    #    hardcoded-False tautology): no authority key is truthy, and approval is
    #    explicitly a forbidden action.
    def test_artifacts_grant_no_approval_authority(self) -> None:
        profile = j0.journey0_authority_profile()
        grant_keys = {k: v for k, v in profile.items() if k != "forbidden_actions"}
        self.assertTrue(grant_keys)  # there are grant flags to check
        self.assertFalse(any(bool(v) for v in grant_keys.values()))
        self.assertFalse(profile["grants_approval_authority"])
        self.assertTrue(
            any("approval" in action for action in profile["forbidden_actions"])
        )

    # 7. Journey 0 artifacts do not authorize implementation or work orders.
    def test_artifacts_do_not_authorize_implementation_or_work_orders(self) -> None:
        profile = j0.journey0_authority_profile()
        self.assertFalse(profile["authorizes_implementation"])
        self.assertFalse(profile["authorizes_work_orders"])
        forbidden = " | ".join(j0.FORBIDDEN_ACTIONS)
        for needle in (
            "work orders",
            "authorize implementation",
            "invoke SpecKit",
            "mutate the target repo",
        ):
            self.assertIn(needle, forbidden)

    # 8. Journey 0 hands off to Journey 1 ONLY as evidence/gap input -- carrying
    #    no approval/implementation authority and no accepted CONFLICT facts.
    def test_handoff_to_journey1_is_evidence_and_gap_input_only(self) -> None:
        handoff = j0.build_journey1_handoff(
            _evidence_pack(j0.EVIDENCE_OBSERVED, j0.EVIDENCE_CONFLICT),
            _gap_report(),
            _decision_register("OPEN"),
        )
        self.assertEqual(handoff["handoff_kind"], j0.HANDOFF_EVIDENCE_AND_GAP_INPUT)
        self.assertEqual(handoff["to_journey"], "journey1")
        # No authority granted through the handoff.
        grant_keys = {
            k: v for k, v in handoff["authority"].items() if k != "forbidden_actions"
        }
        self.assertFalse(any(bool(v) for v in grant_keys.values()))
        # A CONFLICT in the evidence is preserved as evidence but never an accepted fact.
        self.assertTrue(
            all(f["label"] == j0.EVIDENCE_OBSERVED for f in handoff["accepted_facts"])
        )
        self.assertEqual(len(handoff["evidence"]), 2)
        # The handoff exposes no top-level approval/work-order/execution grant key.
        for forbidden_key in ("approval", "work_orders", "implementation_authorized"):
            self.assertNotIn(forbidden_key, handoff)


if __name__ == "__main__":
    unittest.main()
