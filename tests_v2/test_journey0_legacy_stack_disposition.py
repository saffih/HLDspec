"""Disposition tests for the legacy Journey 0 dict/contracts stack."""
from __future__ import annotations

import inspect
import unittest

from hldspec import journey0_artifact_contracts as artifact_contracts
from hldspec import journey0_draftability_gate as draftability_gate
from hldspec import journey0_filesystem_fixture_collector as filesystem_fixture_collector
from hldspec import journey0_synthetic_evidence_collector as synthetic_evidence_collector


LEGACY_MODULES = (
    artifact_contracts,
    draftability_gate,
    synthetic_evidence_collector,
    filesystem_fixture_collector,
)


class Journey0LegacyStackDispositionTests(unittest.TestCase):
    def test_legacy_modules_are_marked_not_canonical_and_do_not_wire(self) -> None:
        for module in LEGACY_MODULES:
            with self.subTest(module=module.__name__):
                self.assertEqual(module.LEGACY_JOURNEY0_STACK_STATUS, "NOT_CANONICAL")
                self.assertEqual(
                    module.LEGACY_JOURNEY0_STACK_WIRING_STATUS, "DO_NOT_WIRE"
                )
                self.assertEqual(
                    module.LEGACY_JOURNEY0_STACK_DISPOSITION,
                    "FROZEN_FOR_COMPATIBILITY_PENDING_DEPRECATION",
                )

    def test_legacy_module_docs_point_to_typed_stack(self) -> None:
        for module in LEGACY_MODULES:
            with self.subTest(module=module.__name__):
                doc = inspect.getdoc(module) or ""
                self.assertIn("NOT_CANONICAL", doc)
                self.assertIn("DO_NOT_WIRE", doc)
                self.assertIn("typed", doc)
                self.assertIn("Journey 0", doc)


if __name__ == "__main__":
    unittest.main()
