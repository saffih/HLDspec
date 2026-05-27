from __future__ import annotations

import unittest

from hldspec.spec_bundle_validator import validate_bundle_queue
from hldspec.spec_bundles import plan_bundles_from_items


def item(feature_id: str, title: str, *, layer: str = "core", deps: list[str] | None = None, contracts: list[str] | None = None, data: list[str] | None = None) -> dict:
    return {
        "order": int(feature_id[-1]) if feature_id[-1].isdigit() else 1,
        "feature_id": feature_id,
        "feature_name": title,
        "depends_on_features": deps or [],
        "architecture_context": {
            "layer": layer,
            "contracts": contracts or [],
            "data_objects": data or [],
        },
        "speckit_specify_input": f"Build {title}.",
    }


class SpecBundlePlannerTests(unittest.TestCase):
    def test_empty_queue(self) -> None:
        self.assertEqual([], plan_bundles_from_items([]))

    def test_single_spec_creates_one_bundle(self) -> None:
        bundles = plan_bundles_from_items([item("F1", "API foundation")])
        self.assertEqual(1, len(bundles))
        self.assertEqual(["F1"], [s["feature_id"] for s in bundles[0]["included_specs"]])

    def test_all_specs_appear_once_and_order_is_preserved(self) -> None:
        items = [
            item("F1", "API foundation", contracts=["api"]),
            item("F2", "API command", deps=["F1"], contracts=["api"]),
            item("F3", "API session", deps=["F2"], contracts=["api"]),
        ]
        bundles = plan_bundles_from_items(items)
        actual = [spec["feature_id"] for bundle in bundles for spec in bundle["included_specs"]]
        self.assertEqual(["F1", "F2", "F3"], actual)

    def test_layer_seam_creates_boundary(self) -> None:
        bundles = plan_bundles_from_items(
            [
                item("F1", "API foundation", layer="api", contracts=["api"]),
                item("F2", "Operational runbook", layer="ops", contracts=["ops"]),
            ]
        )
        self.assertEqual(2, len(bundles))

    def test_shared_contracts_prevent_unnecessary_cut(self) -> None:
        bundles = plan_bundles_from_items(
            [
                item("F1", "API foundation", layer="api", contracts=["shared-api"]),
                item("F2", "API command", layer="api", deps=["F1"], contracts=["shared-api"]),
            ]
        )
        self.assertEqual(1, len(bundles))

    def test_semantic_split_within_same_layer(self) -> None:
        bundles = plan_bundles_from_items(
            [
                item("F1", "API command", layer="core", contracts=["api"]),
                item("F2", "Security reliability guard", layer="core", contracts=["security"]),
            ]
        )
        self.assertEqual(1, len(bundles), "soft semantic seams should not over-split tiny adjacent groups")

    def test_hard_max_size_is_enforced(self) -> None:
        items = [item(f"F{i}", f"API command {i}", contracts=["api"]) for i in range(1, 7)]
        bundles = plan_bundles_from_items(items)
        self.assertTrue(all(len(bundle["included_specs"]) <= 5 for bundle in bundles))

    def test_validator_catches_forward_dependency(self) -> None:
        queue = {"items": [item("F1", "One"), item("F2", "Two", deps=["F1"])]}
        bundle_queue = {
            "bundles": [
                {
                    "bundle_id": "G01",
                    "bundle_name": "One",
                    "bundle_slug": "g01-one",
                    "included_specs": [{"feature_id": "F1", "depends_on_features": ["F2"]}],
                    "why_grouped": "single",
                    "dependency_position": 1,
                    "dependencies": ["F2"],
                    "allowed_evidence": ["x"],
                    "forbidden_reads": ["y"],
                    "model_runtime_recommendation": {},
                    "expected_outputs": ["z"],
                    "tests_required": ["t"],
                    "runskeptic_checkpoints": ["post-plan"],
                    "human_checkpoint_rules": ["stop"],
                    "stop_condition": "stop",
                    "implementation_allowed": False,
                    "prompt_paths": {},
                },
                {
                    "bundle_id": "G02",
                    "bundle_name": "Two",
                    "bundle_slug": "g02-two",
                    "included_specs": [{"feature_id": "F2", "depends_on_features": []}],
                    "why_grouped": "single",
                    "dependency_position": 2,
                    "dependencies": [],
                    "allowed_evidence": ["x"],
                    "forbidden_reads": ["y"],
                    "model_runtime_recommendation": {},
                    "expected_outputs": ["z"],
                    "tests_required": ["t"],
                    "runskeptic_checkpoints": ["post-plan"],
                    "human_checkpoint_rules": ["stop"],
                    "stop_condition": "stop",
                    "implementation_allowed": False,
                    "prompt_paths": {},
                },
            ]
        }
        findings = validate_bundle_queue(bundle_queue, queue)
        self.assertTrue(any(f.check == "forward_dependency" for f in findings))

    def test_validator_requires_core_fields(self) -> None:
        queue = {"items": [item("F1", "One")]}
        bundle_queue = {"bundles": [{"bundle_id": "G01", "included_specs": [{"feature_id": "F1"}]}]}
        findings = validate_bundle_queue(bundle_queue, queue)
        checks = {finding.check for finding in findings}
        self.assertIn("bundle_schema", checks)
        self.assertIn("allowed_evidence", checks)
        self.assertIn("forbidden_reads", checks)
        self.assertIn("tests_required", checks)
        self.assertIn("runskeptic_checkpoints", checks)
        self.assertIn("human_checkpoint_rules", checks)


if __name__ == "__main__":
    unittest.main()
