from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_speckit_prework_quality_review.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_speckit_prework_quality_review", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SpeckitPreworkQualityReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = load_module()

    def _make_minimal_inputs(self, with_testing_axiom: bool) -> tuple[dict, dict, dict, dict, dict, dict]:
        rules = [
            {
                "rule_id": "ARCH-001",
                "rationale": "baseline architecture coverage",
            }
        ]
        if with_testing_axiom:
            rules.append(
                {
                    "rule_id": "ENG-001",
                    "rationale": "engineering_toolbox:testing.design_for_testability",
                }
            )
        constitution = {
            "required_rules": rules,
            "human_checkpoint": {"human_decision": "TBD"},
        }
        manifest = {"features": [{"feature_id": "001", "feature_name": "Foundation", "depends_on_features": []}]}
        graph = {"bottom_up_order": ["001"]}
        queue = {"items": [{"feature_id": "001"}]}
        usecase_map = {"feature_candidates": [{"feature_id": "001"}], "status": "APPROVAL_READY"}
        dossier_quality = {"status": "APPROVAL_READY"}
        return manifest, graph, constitution, queue, usecase_map, dossier_quality

    def test_flags_missing_testing_axiom(self) -> None:
        manifest, graph, constitution, queue, usecase_map, dossier_quality = self._make_minimal_inputs(False)
        findings = self.mod.build_findings(manifest, graph, constitution, queue, usecase_map, dossier_quality)
        qg019 = [finding for finding in findings if finding["id"] == "QG-019"]
        self.assertEqual(1, len(qg019))
        self.assertEqual("BLOCKER", qg019[0]["severity"])
        self.assertIn("every product fully tested", qg019[0]["finding"])
        self.assertIn("build_speckit_constitution_from_toolbox.py", qg019[0]["recommendation"])

    def test_does_not_flag_when_testing_axiom_present(self) -> None:
        manifest, graph, constitution, queue, usecase_map, dossier_quality = self._make_minimal_inputs(True)
        findings = self.mod.build_findings(manifest, graph, constitution, queue, usecase_map, dossier_quality)
        self.assertFalse(any(finding["id"] == "QG-019" for finding in findings))


if __name__ == "__main__":
    unittest.main()
