from __future__ import annotations

import unittest
from typing import Any

from hldspec.ports import ArtifactStorePort, HumanDecisionPort


class TestHumanDecisionPort(unittest.TestCase):
    def test_human_decision_port_is_protocol(self):
        from typing import Protocol
        self.assertTrue(issubclass(HumanDecisionPort, Protocol))

    def test_artifact_store_port_is_protocol(self):
        from typing import Protocol
        self.assertTrue(issubclass(ArtifactStorePort, Protocol))

    def test_concrete_class_satisfies_human_decision_port(self):
        class ConcreteHumanDecision:
            def present_checkpoint(self, checkpoint: Any) -> str:
                return "next"

            def record_decision(self, question_id: str, decision: str, rationale: str = "") -> None:
                pass

        obj = ConcreteHumanDecision()
        self.assertIsInstance(obj, HumanDecisionPort)


if __name__ == "__main__":
    unittest.main()
