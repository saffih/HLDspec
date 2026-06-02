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


HLD_TEXT = """# Scope-aware dossier fixture

## HLD-001 - Excluded Unix Socket Surface

HLD-ID: HLD-001
HLD-ROLE: architecture
HLD-DESC: HLD-001 is out_of_scope architecture at high risk, touching socket; "unix socket protocol contract".

This out-of-scope section still says unix socket protocol contract, which would be
enough to mint a contract if only HLD-ROLE were considered.

## HLD-002 - In Scope Unix Socket Surface

HLD-ID: HLD-002
HLD-ROLE: architecture
HLD-DESC: HLD-002 is in_scope architecture at high risk, touching socket; "unix socket protocol contract".

This in-scope section defines the unix socket protocol contract, including request
framing and response framing.
"""


class DossierScopeAwareTests(unittest.TestCase):
    def test_scope_exclusion_blocks_contract_minting(self) -> None:
        sections = dossier.parse_hld_sections(HLD_TEXT)
        self.assertEqual(sections[0]["scope"], "out_of_scope")
        self.assertEqual(sections[1]["scope"], "in_scope")

        # Keep the signal gate open so the regression isolates scope gating.
        chunk_map = {
            "sections": [
                {"hld_id": section["hld_id"], "architect_signal": "high"}
                for section in sections
            ]
        }
        contract_map = dossier.build_interface_contract_map(sections, chunk_map)
        contracts = contract_map["contracts"]
        source_ids = {sid for contract in contracts for sid in contract["source_hld_sections"]}

        self.assertEqual(source_ids, {"HLD-002"})
        self.assertEqual(len(contracts), 1)
        self.assertNotIn("HLD-001", source_ids)


if __name__ == "__main__":
    unittest.main()
