from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MODULE_PATH = ROOT / "scripts" / "classify_hld_sections.py"
SPEC = importlib.util.spec_from_file_location("classify_hld_sections", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load {MODULE_PATH}")
classify_hld_sections = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(classify_hld_sections)


class FakeSection:
    def __init__(self, title: str, *, role: str = "", text: str = "", hld_specs: str = "TBD") -> None:
        self.id = "HLD-001"
        self.title = title
        self.text = text
        self._metadata = {
            "HLD-ROLE": role,
            "HLD-SPECS": hld_specs,
        }

    def metadata_value(self, key: str, default: str = "") -> str:
        return self._metadata.get(key, default)


def classify(title: str, *, role: str = "", text: str = "", hld_specs: str = "TBD") -> dict[str, object]:
    return classify_hld_sections.classify_section(
        FakeSection(title, role=role, text=text, hld_specs=hld_specs),
        previous_spec_candidate="HLD-000",
    )


class HldSectionClassificationContextTest(unittest.TestCase):
    def assert_kind(self, title: str, expected_kind: str, *, role: str = "", text: str = "") -> None:
        item = classify(title, role=role, text=text)
        self.assertEqual(item["section_kind"], expected_kind, title)
        self.assertEqual(item["spec_candidate"], expected_kind == "SPEC_CANDIDATE", title)

    def test_context_only_false_positive_titles_are_not_spec_candidates(self) -> None:
        for title in [
            "Stakeholder Analysis",
            "User Personas",
            "Business Case Foundation",
            "Executive Summary",
            "Assumptions",
            "Milestones",
        ]:
            with self.subTest(title=title):
                item = classify(title)
                self.assertEqual(item["section_kind"], "HLD_CONTEXT_ONLY")
                self.assertFalse(item["spec_candidate"])
                self.assertEqual(item["recommended_action"], "KEEP_AS_CONTEXT")

    def test_governance_titles_are_not_spec_candidates(self) -> None:
        for title in ["Decision Log", "Open Conflict", "Open Conflicts"]:
            with self.subTest(title=title):
                item = classify(title)
                self.assertEqual(item["section_kind"], "GOVERNANCE")
                self.assertFalse(item["spec_candidate"])
                self.assertEqual(item["recommended_action"], "KEEP_AS_GOVERNANCE_CONTEXT")

    def test_buildable_title_still_remains_spec_candidate(self) -> None:
        item = classify("Database API Interface")
        self.assertEqual(item["section_kind"], "SPEC_CANDIDATE")
        self.assertTrue(item["spec_candidate"])
        self.assertEqual(item["recommended_action"], "PLAN_AS_SPEC_CANDIDATE")

    def test_explicit_hld_specs_override_context_title(self) -> None:
        item = classify("Stakeholder Analysis", hld_specs="004")
        self.assertEqual(item["section_kind"], "SPEC_CANDIDATE")
        self.assertTrue(item["spec_candidate"])
        self.assertEqual(item["recommended_action"], "USE_EXPLICIT_HLD_SPECS")

    def test_unknown_default_stays_spec_candidate(self) -> None:
        item = classify("Deployment Model")
        self.assertEqual(item["section_kind"], "SPEC_CANDIDATE")
        self.assertTrue(item["spec_candidate"])


if __name__ == "__main__":
    unittest.main()
