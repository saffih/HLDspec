from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HldspecV2FlowTestDocTests(unittest.TestCase):
    def test_flow_test_doc_exists_and_defines_safety_contract(self) -> None:
        text = (ROOT / "docs" / "HLDSPEC_V2_FLOW_TEST.md").read_text(encoding="utf-8")

        for item in [
            "HLDspec V2 Flow Test",
            "CHECKPOINT_REACHED",
            "SpecKit invoked: false",
            "The runner may modify only its workspace",
            "Flow-System-HLD.md",
        ]:
            self.assertIn(item, text)


if __name__ == "__main__":
    unittest.main()
