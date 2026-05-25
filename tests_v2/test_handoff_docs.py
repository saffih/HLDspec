from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec.handoff_docs import write_handoff_docs
from hldspec.machines.speckit_prework import SpeckitPreworkMachine
from hldspec.state_machine import MachineContext, MachineStatus


class HandoffDocsTests(unittest.TestCase):
    def make_sync(self) -> Path:
        sync = Path(tempfile.mkdtemp()) / "firstrun" / ".specify" / "sync"
        sync.mkdir(parents=True)

        (sync / "spec_build_plan.json").write_text(
            json.dumps(
                {
                    "plan_quality": {
                        "decision": "DECOMPOSE",
                        "recommendation": "SPLIT_PLANNED_SPEC",
                        "conflicts": [],
                    },
                    "planned_specs": [
                        {
                            "planned_spec_id": "010",
                            "title": "Flow Core Database API",
                            "quality_flags": ["data_api_boundary_needs_review"],
                            "requires_user_review": True,
                            "recommendation": "KEEP_SPEC",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (sync / "spec_build_plan_gate_decision.json").write_text(
            json.dumps(
                {
                    "decision": "ACCEPT_WITH_RATIONALE",
                    "rationale": "Intentional API boundary.",
                    "accepted_flagged_specs": ["010"],
                }
            ),
            encoding="utf-8",
        )
        for name in [
            "feature_dependency_graph.md",
            "constitution_update_plan.md",
            "spec_build_plan_review.md",
            "speckit_proxy_dossier.md",
            "speckit_input_manifest.md",
            "speckit_invocation_queue.md",
            "target_spec_work_order.md",
            "speckit_prework_package.md",
            "speckit_prework_quality_review.md",
            "hldspec_state.md",
        ]:
            (sync / name).write_text(f"# {name}\n\ncontent\n", encoding="utf-8")

        (sync / "speckit_prework_quality_review.json").write_text(
            json.dumps({"status": "PASS", "findings": []}),
            encoding="utf-8",
        )

        return sync

    def test_write_handoff_docs_creates_architecture_and_product_docs(self) -> None:
        sync = self.make_sync()
        architecture, product = write_handoff_docs(sync)

        self.assertTrue(architecture.exists())
        self.assertTrue(product.exists())

        architecture_text = architecture.read_text(encoding="utf-8")
        product_text = product.read_text(encoding="utf-8")

        self.assertIn("# Architecture Handoff", architecture_text)
        self.assertNotIn("made by AI", architecture_text)
        self.assertIn("Flow Core Database API", architecture_text)
        self.assertIn("Intentional API boundary.", architecture_text)

        self.assertIn("# Product Handoff", product_text)
        self.assertIn("Product correctness guard", product_text)
        self.assertIn("Flow Core Database API", product_text)

    def test_speckit_prework_machine_does_not_generate_handoff_docs(self) -> None:
        # write_handoff_docs() was moved to ProjectMachine (orchestration layer).
        # SpeckitPreworkMachine is a gate only — it must not write handoff docs.
        sync = self.make_sync()
        workspace = sync.parents[2]

        result = SpeckitPreworkMachine().run(
            MachineContext(repo_root=".", source_hld="source.md", workspace=str(workspace))
        )

        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("SPECKIT_PREWORK_READY_FOR_APPROVAL", result.state)
        self.assertFalse((sync / "architecture_handoff.md").exists())
        self.assertFalse((sync / "product_handoff.md").exists())
        roles = {artifact.role for artifact in result.artifacts_written}
        self.assertNotIn("architecture_handoff", roles)
        self.assertNotIn("product_handoff", roles)


if __name__ == "__main__":
    unittest.main()
