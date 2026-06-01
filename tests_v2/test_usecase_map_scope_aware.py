from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

import hld_map

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_hld_usecase_api_map.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = load_module("build_hld_usecase_api_map", SCRIPT)


def section(sid: str, title: str, desc: str | None, prose: str) -> str:
    lines = [
        f"## {sid} - {title}",
        "",
        f"HLD-ID: {sid}",
        "HLD-ROLE: processing",
        "HLD-STATUS: active",
        "HLD-RISK: LOW",
        "HLD-SPECS: TBD",
        "HLD-RESOURCES: TBD",
    ]
    if desc is not None:
        lines.append(f"HLD-DESC: {desc}")
    lines.extend(["", prose, ""])
    return "\n".join(lines)


class UsecaseMapScopeAwareTests(unittest.TestCase):
    def test_non_goal_classification_prefers_canonical_scope(self) -> None:
        hld_text = (
            section(
                "HLD-001",
                "Excluded",
                'HLD-001 is out-of-scope processing at low risk, touching none; "deliberately excluded".',
                "This section mentions a non-goal keyword in prose, but should be classified by scope.",
            )
            + section(
                "HLD-002",
                "Fallback",
                None,
                "This is a must not build here note that should still fall back to keyword detection.",
            )
            + section(
                "HLD-003",
                "In scope",
                'HLD-003 is in-scope processing at low risk, touching none; "authoritative in scope".',
                "This section says must not do that in prose, but the canonical line keeps it in scope.",
            )
        )
        parsed = hld_map.parse_hld_text(hld_text, source_path="HLD.md")

        with tempfile.TemporaryDirectory() as tmpdir:
            data = mod.build_map(parsed, Path(tmpdir))

        non_goal_ids = {
            item["source_hld_sections"][0]
            for item in data["non_goals"]
        }

        self.assertIn("HLD-001", non_goal_ids)
        self.assertIn("HLD-002", non_goal_ids)
        self.assertNotIn("HLD-003", non_goal_ids)


if __name__ == "__main__":
    unittest.main()
