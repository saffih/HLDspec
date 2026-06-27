"""Tests for the synthetic Journey 0 evidence collector."""
from __future__ import annotations

import inspect
import unittest

from hldspec import journey0_artifact_contracts as j0
from hldspec import journey0_synthetic_evidence_collector as collector


def _evidence(label: str, statement: str) -> collector.SyntheticEvidence:
    return collector.SyntheticEvidence(label=label, statement=statement)


def _collect(
    fixture: collector.SyntheticBrownfieldInput,
) -> tuple[collector.SyntheticJourney0Artifacts, object]:
    artifacts = collector.collect_synthetic_brownfield_evidence(fixture)
    result = collector.evaluate_synthetic_brownfield_fixture(fixture)
    return artifacts, result


class Journey0SyntheticEvidenceCollectorTests(unittest.TestCase):
    def test_clean_synthetic_fixture_reaches_ready_to_draft(self) -> None:
        artifacts, result = _collect(
            collector.SyntheticBrownfieldInput(
                evidence=(
                    _evidence(j0.EVIDENCE_OBSERVED, "product evidence: run dashboard"),
                    _evidence(j0.EVIDENCE_OBSERVED, "code evidence: resumable job model"),
                    _evidence(j0.EVIDENCE_OBSERVED, "spec evidence: operator review"),
                )
            )
        )

        self.assertEqual(
            artifacts.evidence_pack["kind"], j0.ARTIFACT_BROWNFIELD_EVIDENCE_PACK
        )
        self.assertEqual(len(j0.accepted_facts(artifacts.evidence_pack)), 3)
        self.assertEqual(result.verdict, j0.VERDICT_READY_TO_DRAFT_HLD)

    def test_product_decision_fixture_preserves_decision_required(self) -> None:
        artifacts, result = _collect(
            collector.SyntheticBrownfieldInput(
                evidence=(
                    _evidence(
                        j0.EVIDENCE_PRODUCT_DECISION_REQUIRED,
                        "resume model owner is unresolved",
                    ),
                ),
                product_decisions=(
                    collector.SyntheticDecision(
                        id="PD-resume-model",
                        status="PRODUCT_DECISION_REQUIRED",
                        question="Who owns resume semantics?",
                    ),
                ),
            )
        )

        self.assertEqual(
            artifacts.evidence_pack["evidence"][0]["label"],
            j0.EVIDENCE_PRODUCT_DECISION_REQUIRED,
        )
        self.assertEqual(
            result.verdict, j0.VERDICT_BLOCKED_PRODUCT_DECISIONS_REQUIRED
        )
        self.assertIn("PD-resume-model", result.blockers[0])

    def test_conflict_fixture_preserves_conflict_for_repo_state_block(self) -> None:
        artifacts, result = _collect(
            collector.SyntheticBrownfieldInput(
                evidence=(
                    _evidence(
                        j0.EVIDENCE_OBSERVED,
                        "HLD fragment says external controller owns lifecycle",
                    ),
                    _evidence(
                        j0.EVIDENCE_CONFLICT,
                        "code/spec evidence says local state owns lifecycle",
                    ),
                ),
                repo_state_conflict=True,
            )
        )

        labels = [item["label"] for item in artifacts.evidence_pack["evidence"]]
        self.assertIn(j0.EVIDENCE_CONFLICT, labels)
        self.assertTrue(artifacts.gap_report["repo_state_conflict"])
        self.assertEqual(result.verdict, j0.VERDICT_BLOCKED_REPO_STATE_CONFLICT)

    def test_insufficient_evidence_fixture_stays_insufficient(self) -> None:
        _, result = _collect(
            collector.SyntheticBrownfieldInput(
                evidence=(
                    _evidence(j0.EVIDENCE_UNKNOWN, "product owner is unknown"),
                    _evidence(j0.EVIDENCE_INFERRED, "resume behavior may exist"),
                )
            )
        )

        self.assertEqual(result.verdict, j0.VERDICT_INSUFFICIENT_EVIDENCE)
        self.assertEqual(result.accepted_fact_count, 0)

    def test_unknown_backed_requirement_fixture_is_not_ready(self) -> None:
        artifacts, result = _collect(
            collector.SyntheticBrownfieldInput(
                evidence=(_evidence(j0.EVIDENCE_OBSERVED, "run records exist"),),
                candidate_requirements=(
                    collector.SyntheticRequirement(
                        id="REQ-agent-can-resume",
                        evidence_label=j0.EVIDENCE_UNKNOWN,
                        statement="agent may resume blocked runs",
                    ),
                ),
            )
        )

        self.assertEqual(
            artifacts.candidate_requirements[0]["evidence_label"],
            j0.EVIDENCE_UNKNOWN,
        )
        self.assertNotEqual(result.verdict, j0.VERDICT_READY_TO_DRAFT_HLD)
        self.assertEqual(result.verdict, j0.VERDICT_INSUFFICIENT_EVIDENCE)

    def test_safety_authority_fixture_blocks_and_grants_no_authority(self) -> None:
        artifacts, result = _collect(
            collector.SyntheticBrownfieldInput(
                evidence=(_evidence(j0.EVIDENCE_OBSERVED, "blocked runs exist"),),
                safety_authority_gaps=(
                    "unclear whether an agent can approve transitions",
                    "unclear whether an agent can execute resume actions",
                ),
            )
        )

        self.assertEqual(
            result.verdict, j0.VERDICT_BLOCKED_PRODUCT_DECISIONS_REQUIRED
        )
        self.assertFalse(result.grants_approval_authority)
        self.assertFalse(result.authorizes_implementation)
        self.assertFalse(result.authorizes_work_orders)
        self.assertFalse(artifacts.authority["grants_approval_authority"])
        self.assertFalse(artifacts.authority["authorizes_implementation"])
        self.assertFalse(artifacts.authority["authorizes_work_orders"])

    def test_collector_output_grants_no_execution_or_work_order_authority(self) -> None:
        artifacts, result = _collect(
            collector.SyntheticBrownfieldInput(
                evidence=(_evidence(j0.EVIDENCE_OBSERVED, "product route exists"),)
            )
        )
        payload = artifacts.to_dict()

        self.assertEqual(result.handoff_kind, j0.HANDOFF_EVIDENCE_AND_GAP_INPUT)
        self.assertTrue(result.journey1_input_only)
        for key in (
            "grants_approval_authority",
            "authorizes_implementation",
            "authorizes_work_orders",
        ):
            self.assertFalse(payload["authority"][key])

    def test_collector_module_has_no_runtime_repo_or_tool_mechanisms(self) -> None:
        source = inspect.getsource(collector)
        forbidden = (
            "open" + "(",
            "write" + "_text",
            "read" + "_text",
            "sub" + "process",
            "os" + ".system",
            "request" + "s",
            "url" + "lib",
            "Spec" + "Kit",
            "cli" + "ck",
            "arg" + "parse",
            "Typ" + "er",
            "Path" + "(",
            "os" + ".walk",
            "glo" + "b",
        )

        for token in forbidden:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
