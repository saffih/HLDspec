from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HldDecisionLogTests(unittest.TestCase):
    def test_write_decision_log_from_queue(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td) / "work"
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)
            queue = {
                "questions": [
                    {
                        "question_id": "Q-001",
                        "source_candidate_id": "HLD-009",
                        "title": "Component Deep-Dive",
                        "question": "Split or keep?",
                        "options": ["SPLIT_AS_PROPOSED", "KEEP_AS_ONE"],
                        "human_decision": "SPLIT_AS_PROPOSED",
                        "human_notes": "Approved split.",
                        "default_proposal": {"proposed_split_plan": []},
                    },
                    {
                        "question_id": "Q-002",
                        "source_candidate_id": "HLD-019",
                        "title": "Milestones",
                        "question": "Keep?",
                        "options": ["KEEP_AS_ONE", "SPLIT"],
                        "human_decision": "TBD",
                    },
                ]
            }
            (sync / "hld_conversion_decision_queue.json").write_text(json.dumps(queue), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "write_hld_decision_log.py"),
                    str(workspace),
                    "--source-hld",
                    "Flow-System-HLD.md",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            data = json.loads((sync / "hld_decision_log.json").read_text(encoding="utf-8"))
            self.assertEqual("HAS_PENDING_DECISIONS", data["status"])
            self.assertEqual(1, data["answered_count"])
            self.assertEqual(1, data["pending_count"])
            appendix = (sync / "hld_source_decision_appendix.md").read_text(encoding="utf-8")
            self.assertIn("HLDSPEC-DECISION-LOG:BEGIN", appendix)
            self.assertIn("Q-001", appendix)

    def test_apply_decision_log_requires_approval_and_replaces_marker(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "HLD.md"
            appendix = Path(td) / "appendix.md"
            source.write_text("# HLD\n\nBody.\n", encoding="utf-8")
            appendix.write_text(
                "<!-- HLDSPEC-DECISION-LOG:BEGIN -->\n\n## HLDspec Decision Log\n\n- Decision: `KEEP_AS_ONE`\n\n<!-- HLDSPEC-DECISION-LOG:END -->\n",
                encoding="utf-8",
            )

            refused = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "apply_hld_decision_log_to_source.py"),
                    str(source),
                    str(appendix),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(2, refused.returncode)

            applied = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "apply_hld_decision_log_to_source.py"),
                    str(source),
                    str(appendix),
                    "--approved",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(0, applied.returncode, msg=applied.stderr)
            text = source.read_text(encoding="utf-8")
            self.assertEqual(1, text.count("HLDSPEC-DECISION-LOG:BEGIN"))

            applied_again = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "apply_hld_decision_log_to_source.py"),
                    str(source),
                    str(appendix),
                    "--approved",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(0, applied_again.returncode, msg=applied_again.stderr)
            text = source.read_text(encoding="utf-8")
            self.assertEqual(1, text.count("HLDSPEC-DECISION-LOG:BEGIN"))


if __name__ == "__main__":
    unittest.main()
