from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_module(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {rel}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dossier = load_module("build_hld_answer_dossier", "scripts/build_hld_answer_dossier.py")

# An HLD with: a real interface section (api), a governance out-of-scope list naming
# excluded machinery, and a purpose section. Only the api section is a contract.
HLD = """# T

## HLD-009 - The CLI contract

HLD-ID: HLD-009
HLD-ROLE: api

The CLI is the interface. Runners use these verbs; no direct database access.

## HLD-011 - Out of scope (deliberately stripped)

HLD-ID: HLD-011
HLD-ROLE: governance

Excluded on purpose: Unix-socket task delivery, health-monitoring daemons, the
HTTP API. Re-introduce only with a documented reason.

## HLD-001 - What it is

HLD-ID: HLD-001
HLD-ROLE: purpose

A CLI-driven task runner. The interface is small.
"""


class DossierContractDerivationTest(unittest.TestCase):
    def setUp(self):
        self.sections = dossier.parse_hld_sections(HLD)
        # Mark every section architect-high so the only thing gating contracts is the
        # role-skip + keyword check, not the signal score.
        self.chunk_map = {
            "sections": [
                {"hld_id": s["hld_id"], "architect_signal": "high"} for s in self.sections
            ]
        }
        self.contracts = dossier.build_interface_contract_map(self.sections, self.chunk_map)["contracts"]
        self.names = {c["contract_name"] for c in self.contracts}
        self.src = {sid for c in self.contracts for sid in c["source_hld_sections"]}

    def test_name_is_derived_from_title_not_hardcoded_vocab(self):
        # The fix removed CONTRACT_NAME_RULES; names must come from the section title.
        self.assertEqual(dossier.contract_name_from_section("The CLI contract"), "The CLI contract Contract")
        self.assertNotIn("Brain-to-Flow CLI Contract", self.names)
        self.assertNotIn("Task Delivery Handshake Contract", self.names)

    def test_out_of_scope_governance_section_mints_no_contract(self):
        # HLD-011 lists excluded machinery; reading it as a feature is the bug.
        self.assertNotIn("HLD-011", self.src)

    def test_purpose_section_mints_no_contract(self):
        self.assertNotIn("HLD-001", self.src)

    def test_real_interface_section_still_produces_a_contract(self):
        # Don't over-suppress: the genuine api section must survive.
        self.assertIn("HLD-009", self.src)


if __name__ == "__main__":
    unittest.main()
