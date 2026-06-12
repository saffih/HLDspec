from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hldspec import phase_evidence as pe


class PhaseEvidenceTests(unittest.TestCase):
    def _assess(self, artifact_text: str | None, evidence_name: str | None = None, evidence_text: str | None = None):
        tmp = tempfile.TemporaryDirectory(prefix="hldspec-phase-evidence-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        artifact = root / "spec.md"
        if artifact_text is not None:
            artifact.write_text(artifact_text, encoding="utf-8")
        candidates = []
        if evidence_name is not None:
            evidence = root / evidence_name
            evidence.write_text(evidence_text or "", encoding="utf-8")
            candidates.append(evidence)
        return pe.assess_phase_artifact(artifact, candidates)

    def test_missing_artifact_is_not_started(self):
        result = self._assess(None)
        self.assertEqual(pe.PHASE_NOT_STARTED, result.phase_state)
        self.assertEqual(pe.EVIDENCE_NONE, result.evidence_state)

    def test_spec_only_is_present_unverified(self):
        result = self._assess("# Spec\n")
        self.assertEqual(pe.PHASE_PRESENT_UNVERIFIED, result.phase_state)
        self.assertEqual(pe.SAFETY_ACTION, result.safety_status)

    def test_markdown_only_evidence_is_unverified(self):
        result = self._assess("# Spec\n", "specify_validation.md", "looks ok\n")
        self.assertEqual(pe.PHASE_PRESENT_UNVERIFIED, result.phase_state)
        self.assertEqual(pe.EVIDENCE_UNVERIFIED, result.evidence_state)

    def test_empty_malformed_and_statusless_json_are_unverified(self):
        for payload in ("", "{not json", "{}", '{"result":"PASS"}'):
            with self.subTest(payload=payload):
                result = self._assess("# Spec\n", "specify_validation.json", payload)
                self.assertEqual(pe.PHASE_PRESENT_UNVERIFIED, result.phase_state)
                self.assertEqual(pe.EVIDENCE_UNVERIFIED, result.evidence_state)

    def test_fail_json_blocks(self):
        result = self._assess("# Spec\n", "specify_validation.json", '{"status":"FAIL"}')
        self.assertEqual(pe.PHASE_BLOCKED, result.phase_state)
        self.assertEqual(pe.SAFETY_BLOCKED, result.safety_status)

    def test_pass_json_verifies_done(self):
        result = self._assess("# Spec\n", "specify_validation.json", '{"status":"PASS"}')
        self.assertEqual(pe.PHASE_DONE_VERIFIED, result.phase_state)
        self.assertEqual(pe.SAFETY_PASS, result.safety_status)


if __name__ == "__main__":
    unittest.main()
