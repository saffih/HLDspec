from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SpeckitProxyProtocolTests(unittest.TestCase):
    def test_proxy_dossier_selects_active_feature_and_question_policy(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)

            (sync / "speckit_input_manifest.json").write_text(
                json.dumps(
                    {
                        "features": [
                            {
                                "feature_id": "001",
                                "feature_name": "Rock Foundation",
                                "short_name": "001-rock-foundation",
                                "source_hld_sections": ["HLD-001"],
                                "depends_on_features": [],
                                "speckit_specify_input": "Build rock foundation from HLD evidence.",
                                "decomposition_flags": [],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (sync / "speckit_invocation_queue.json").write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "order": 1,
                                "feature_id": "001",
                                "feature_name": "Rock Foundation",
                                "short_name": "001-rock-foundation",
                                "status": "READY_FOR_SPECKIT_SPECIFY",
                                "speckit_specify_input": "Build rock foundation from HLD evidence.",
                                "depends_on_features": [],
                                "source_hld_sections": ["HLD-001"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (sync / "constitution_update_plan.json").write_text(
                json.dumps(
                    {
                        "target_constitution_path": ".specify/memory/constitution.md",
                        "required_rules": [
                            {"rule_id": "ARCH-001", "name": "HLD Source of Truth", "rule": "Do not contradict HLD."}
                        ],
                        "human_checkpoint": {"human_decision": "APPROVE_PLAN"},
                    }
                ),
                encoding="utf-8",
            )
            (sync / "feature_dependency_graph.json").write_text(
                json.dumps({"bottom_up_order": ["001"], "edges": []}),
                encoding="utf-8",
            )
            (sync / "speckit_prework_quality_review.json").write_text(
                json.dumps({"status": "APPROVAL_READY", "findings": [], "case_to_present": {"first_feature_case": {"feature_id": "001"}}}),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_speckit_proxy_dossier.py"),
                    str(workspace),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            dossier = json.loads((sync / "speckit_proxy_dossier.json").read_text(encoding="utf-8"))

            self.assertEqual("001", dossier["selected_feature"]["feature_id"])
            self.assertIn("specify", " ".join(dossier["speckit_sequence"]))
            self.assertIn("clarify", " ".join(dossier["speckit_sequence"]))
            self.assertIn("ANSWER_FROM_EVIDENCE", dossier["question_answering_policy"])
            self.assertIn("ESCALATE_TO_HUMAN", dossier["question_answering_policy"])

            report = (sync / "speckit_proxy_dossier.md").read_text(encoding="utf-8")
            self.assertIn("SpecKit Proxy Dossier", report)
            self.assertIn("Question handling", report)
            self.assertIn("Input for /speckit.specify", report)
            self.assertIn("Phase completion report required", report)

    def test_protocol_document_is_referenced(self) -> None:
        protocol = (ROOT / "docs" / "SPECKIT_PROXY_PROTOCOL.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        terms = (ROOT / "TERMINOLOGY.md").read_text(encoding="utf-8")

        self.assertIn("SpecKit Proxy Protocol", protocol)
        self.assertIn("ANSWER_FROM_EVIDENCE", protocol)
        self.assertIn("ESCALATE_TO_HUMAN", protocol)
        self.assertIn("docs/SPECKIT_PROXY_PROTOCOL.md", agents)
        self.assertIn("SpecKit Proxy Subagent", terms)


if __name__ == "__main__":
    unittest.main()
