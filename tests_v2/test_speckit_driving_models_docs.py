"""Anti-drift guard for the canonical SpecKit ritual chain.

Both SpecKit driving models (the HLD pipeline executor and the ad-hoc in-target
navigator) encode the ritual chain independently. This test binds every
representation -- the doc, the invoker's PHASE_SKILL, the executor's PHASE_ORDER,
and the navigator's /speckit.X next-actions -- to one canonical chain so they
cannot silently diverge. See docs/SPECKIT_DRIVING_MODELS.md.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from hldspec import next_feature_agents_md as nfa
from hldspec import next_feature_readiness as nfr
from hldspec import speckit_invoker as inv
from hldspec.machines import speckit_execution as ex

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "SPECKIT_DRIVING_MODELS.md"

# The single source of truth for the SpecKit ritual chain. A deliberate change to
# the ritual must update this tuple and every representation checked below.
CANONICAL_CHAIN = (
    "CONSTITUTION",
    "SPECIFY",
    "CLARIFY",
    "PLAN",
    "CHECKLIST",
    "TASKS",
    "ANALYZE",
    "IMPLEMENT",
)

# Rendered form that must appear verbatim in the doc.
CHAIN_ARROW = " → ".join(CANONICAL_CHAIN)


class SpecKitDrivingModelsDocTests(unittest.TestCase):
    def test_doc_exists_and_documents_both_models(self) -> None:
        self.assertTrue(DOC.is_file(), f"missing {DOC}")
        text = DOC.read_text(encoding="utf-8")
        self.assertIn("HLD pipeline", text)
        self.assertIn("Ad-hoc in-target", text)

    def test_doc_states_canonical_chain(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        self.assertIn(CHAIN_ARROW, text)

    def test_invoker_phase_skill_matches_chain(self) -> None:
        self.assertEqual(CANONICAL_CHAIN, tuple(inv.PHASE_SKILL))

    def test_executor_phase_order_matches_per_feature_chain(self) -> None:
        # CONSTITUTION is the per-project step; the executor's per-feature ritual
        # is the chain from SPECIFY onward, plus the terminal DONE marker.
        self.assertEqual(ex.PHASE_CONSTITUTION, CANONICAL_CHAIN[0])
        self.assertEqual(CANONICAL_CHAIN[1:] + (ex.PHASE_DONE,), tuple(ex.PHASE_ORDER))

    def test_agent_guide_bootstrap_states_canonical_chain(self) -> None:
        # The target-side agent-guidance bootstrap also renders the chain; bind it
        # so it cannot drift from the canonical definition either.
        text = nfa.build_next_feature_agents_md(ROOT)
        self.assertIn(CHAIN_ARROW, text)

    def test_navigator_references_every_chain_step(self) -> None:
        # The ad-hoc navigator drives by emitting /speckit.X next-actions; every
        # canonical step must be reachable as such an action in its source.
        source = (ROOT / "hldspec" / "next_feature_readiness.py").read_text(encoding="utf-8")
        missing = [step for step in CANONICAL_CHAIN if f"/speckit.{step.lower()}" not in source]
        self.assertEqual([], missing, f"navigator missing /speckit.X for: {missing}")


if __name__ == "__main__":
    unittest.main()
