#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def feature_name(item: dict[str, Any]) -> str:
    return str(item.get("feature_name") or item.get("title") or item.get("planned_spec_id") or item.get("feature_id") or "unknown")


def build_findings(manifest: dict[str, Any], graph: dict[str, Any], constitution: dict[str, Any], queue: dict[str, Any], usecase_map: dict[str, Any], dossier_quality: dict[str, Any], spec_list: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    features = [item for item in as_list(manifest.get("features")) if isinstance(item, dict)]
    roots = []
    for feature in features:
        deps = as_list(feature.get("depends_on_features"))
        if not deps:
            roots.append(feature)

    if not usecase_map:
        findings.append(
            {
                "id": "QG-009",
                "severity": "ACTION",
                "area": "use-case/API map",
                "finding": "No hld_usecase_api_map artifact was found for the prework gate.",
                "recommendation": "Run build_hld_usecase_api_map before approving SpecKit handoff.",
                "RunSkeptic_decision": "FIX",
            }
        )
    else:
        feature_candidates = as_list(usecase_map.get("feature_candidates"))
        context_ids = {str(item.get("hld_id")) for item in as_list(usecase_map.get("context_only_sections")) if isinstance(item, dict)}
        map_status = str(usecase_map.get("status", ""))
        if map_status == "REWORK_REQUIRED" or not feature_candidates:
            findings.append(
                {
                    "id": "QG-010",
                    "severity": "BLOCKER",
                    "area": "use-case/API map",
                    "finding": "Use-case/API map did not identify any buildable feature candidates.",
                    "recommendation": "Rebuild HLD classification or add buildable API/data/processing/UI/system sections before SpecKit handoff.",
                    "RunSkeptic_decision": "DECOMPOSE",
                }
            )
        first_feature_for_map = roots[0] if roots else (features[0] if features else {})
        first_source_ids = {str(item) for item in as_list(first_feature_for_map.get("source_hld_sections"))}
        if first_source_ids & context_ids:
            findings.append(
                {
                    "id": "QG-011",
                    "severity": "BLOCKER",
                    "area": "first feature selection",
                    "finding": "First SpecKit feature is sourced from a context-only HLD section.",
                    "recommendation": "Rebuild the spec build plan so the first feature is an independently buildable API/data/processing/UI/system foundation.",
                    "RunSkeptic_decision": "FIX",
                }
            )
        # QG-011b: secondary signal — first feature has no implementable content
        # (catches documentation-as-feature even when section classification is wrong)
        if first_feature_for_map:
            has_use_cases = bool(as_list(first_feature_for_map.get("use_cases")))
            has_user_stories = bool(as_list(first_feature_for_map.get("user_stories")))
            has_user_journeys = bool(as_list(first_feature_for_map.get("user_journeys")))
            has_api_surface = bool(as_list(first_feature_for_map.get("api_surface")))
            has_data_entities = bool(as_list(first_feature_for_map.get("data_entities")))
            no_implementable_content = not any([has_use_cases, has_user_stories, has_user_journeys, has_api_surface, has_data_entities])
            if no_implementable_content:
                findings.append(
                    {
                        "id": "QG-011b",
                        "severity": "BLOCKER",
                        "area": "first feature implementability",
                        "finding": (
                            f"First feature '{feature_name(first_feature_for_map)}' has no use_cases, user_stories, user_journeys, "
                            "api_surface, or data_entities — it is likely a documentation or overview section, not a buildable feature."
                        ),
                        "recommendation": (
                            "Select a first feature that has at least one of: use cases, user stories, API surface, or data entities. "
                            "Architecture overview sections should not be the first SpecKit invocation."
                        ),
                        "RunSkeptic_decision": "FIX",
                    }
                )

    if not features:
        findings.append(
            {
                "id": "QG-001",
                "severity": "BLOCKER",
                "area": "feature extraction",
                "finding": "No SpecKit features were extracted.",
                "recommendation": "Rebuild the SpecKit input manifest from the HLD before approval.",
                "RunSkeptic_decision": "DECOMPOSE",
            }
        )

    if features and not roots:
        findings.append(
            {
                "id": "QG-002",
                "severity": "BLOCKER",
                "area": "dependency graph",
                "finding": "No independent/root feature exists; every feature depends on another feature.",
                "recommendation": "Review the dependency graph for a cycle or missing foundation feature.",
                "RunSkeptic_decision": "CONFLICT",
            }
        )

    for feature in features:
        if not str(feature.get("speckit_specify_input", "")).strip():
            findings.append(
                {
                    "id": "QG-003",
                    "severity": "BLOCKER",
                    "area": "SpecKit input",
                    "finding": f"{feature_name(feature)} has no natural-language input for /speckit.specify.",
                    "recommendation": "Add a clear feature description before invoking SpecKit.",
                    "RunSkeptic_decision": "FIX",
                }
            )
        if "SPLIT_API_CONTRACT_FROM_PROCESSING" in as_list(feature.get("decomposition_flags")):
            findings.append(
                {
                    "id": "QG-004",
                    "severity": "ACTION",
                    "area": "decomposition",
                    "finding": f"{feature_name(feature)} may mix API/interface contract with processing behavior.",
                    "recommendation": "Judge should explain whether this is split, sequenced, or intentionally kept together before approval.",
                    "RunSkeptic_decision": "DECOMPOSE",
                }
            )
        if "EXTRACT_COMMON_FOUNDATION" in as_list(feature.get("decomposition_flags")) and as_list(feature.get("depends_on_features")):
            findings.append(
                {
                    "id": "QG-005",
                    "severity": "ACTION",
                    "area": "common foundation",
                    "finding": f"{feature_name(feature)} is a common/foundation candidate but has dependencies.",
                    "recommendation": "Verify whether the common foundation should be earlier or split into a root foundation.",
                    "RunSkeptic_decision": "DECOMPOSE",
                }
            )

    rules = [item for item in as_list(constitution.get("required_rules")) if isinstance(item, dict)]
    if not rules:
        findings.append(
            {
                "id": "QG-006",
                "severity": "BLOCKER",
                "area": "constitution",
                "finding": "No constitution rules were proposed.",
                "recommendation": "Generate constitution rules that protect HLD architecture before invoking SpecKit.",
                "RunSkeptic_decision": "FIX",
            }
        )

    has_testing_axiom = any(
        "engineering_toolbox:testing.design_for_testability" in str(r.get("rationale", ""))
        for r in rules
    )
    if not has_testing_axiom:
        findings.append(
            {
                "id": "QG-019",
                "severity": "BLOCKER",
                "area": "constitution testing coverage",
                "finding": "Mandatory 'every product fully tested' axiom is not present in the constitution plan.",
                "recommendation": "Run build_speckit_constitution_from_toolbox.py to add the engineering-toolbox testing axiom.",
                "RunSkeptic_decision": "FIX",
            }
        )

    checkpoint = constitution.get("human_checkpoint", {})
    if isinstance(checkpoint, dict) and checkpoint.get("human_decision") not in ("TBD", "", None):
        findings.append(
            {
                "id": "QG-007",
                "severity": "ACTION",
                "area": "approval state",
                "finding": "Constitution checkpoint already has a human decision.",
                "recommendation": "Ensure the review reflects the latest human decision and affected artifacts were rebuilt.",
                "RunSkeptic_decision": "VERIFY",
            }
        )

    graph_order = as_list(graph.get("bottom_up_order"))
    queue_items = [item for item in as_list(queue.get("items")) if isinstance(item, dict)]
    queue_order = [str(item.get("feature_id")) for item in queue_items]
    if graph_order and queue_order and [str(item) for item in graph_order] != queue_order:
        findings.append(
            {
                "id": "QG-008",
                "severity": "BLOCKER",
                "area": "ordering",
                "finding": "SpecKit invocation queue order does not match dependency graph bottom-up order.",
                "recommendation": "Rebuild the invocation queue from the dependency graph.",
                "RunSkeptic_decision": "FIX",
            }
        )

    # QG-017: check for spec ID conflicts with existing project specs
    if spec_list is not None:
        existing_scan = spec_list.get("existing_specs_scan") or {}
        conflicts = as_list(existing_scan.get("conflicts"))
        if conflicts:
            conflict_summary = "; ".join(
                f"{c.get('planned_id')} conflicts with {', '.join(c.get('conflicts_with', []))}"
                for c in conflicts[:5]
            )
            findings.append(
                {
                    "id": "QG-017",
                    "severity": "BLOCKER",
                    "area": "spec ID conflicts",
                    "finding": (
                        f"{len(conflicts)} planned spec ID(s) conflict with existing project specs: {conflict_summary}"
                    ),
                    "recommendation": (
                        "Re-run build_hldspec_speckit_spec_list.py with --source-project so new IDs start after "
                        "the highest existing spec number. Do not overwrite existing project specs."
                    ),
                    "RunSkeptic_decision": "FIX",
                }
            )
        elif existing_scan.get("found") and existing_scan.get("existing_count", 0) > 0:
            findings.append(
                {
                    "id": "QG-017-info",
                    "severity": "ACTION",
                    "area": "spec ID conflicts",
                    "finding": (
                        f"Source project has {existing_scan['existing_count']} existing spec(s); "
                        f"new specs start at {existing_scan.get('highest_number', 0) + 1:03d}. No ID conflicts detected."
                    ),
                    "recommendation": "Verify that the new spec decomposition complements (not duplicates) the existing specs.",
                    "RunSkeptic_decision": "VERIFY",
                }
            )
            non_historical = as_list(existing_scan.get("non_historical_ids"))
            if non_historical:
                sample = ", ".join(str(item) for item in non_historical[:5])
                findings.append(
                    {
                        "id": "QG-018",
                        "severity": "ACTION",
                        "area": "spec history classification",
                        "finding": (
                            f"{len(non_historical)} existing spec(s) are not historical because their Feature Branch "
                            f"was not found in first-parent merge history: {sample}"
                        ),
                        "recommendation": (
                            "Treat these specs as active/unmerged context, not completed history. "
                            "Only specs classified MERGED_DONE may be used as historical baseline."
                        ),
                        "RunSkeptic_decision": "VERIFY",
                    }
                )

    if not dossier_quality:
        findings.append(
            {
                "id": "QG-012",
                "severity": "BLOCKER",
                "area": "Answer Dossier",
                "finding": "No HLD Answer Dossier quality review was found.",
                "recommendation": "Run build_hld_answer_dossier.py before approving SpecKit prework.",
                "RunSkeptic_decision": "FIX",
            }
        )
    else:
        dossier_status = str(dossier_quality.get("status", "MISSING"))
        if dossier_status == "REWORK_REQUIRED":
            findings.append(
                {
                    "id": "QG-013",
                    "severity": "BLOCKER",
                    "area": "Answer Dossier",
                    "finding": "HLD Answer Dossier quality gate requires rework.",
                    "recommendation": "Fix hld_answer_dossier_quality_review findings before SpecKit approval.",
                    "RunSkeptic_decision": "FIX",
                }
            )
        elif dossier_status == "APPROVAL_READY_WITH_ACTIONS":
            findings.append(
                {
                    "id": "QG-014",
                    "severity": "ACTION",
                    "area": "Answer Dossier",
                    "finding": "HLD Answer Dossier is present but has action findings.",
                    "recommendation": "Judge should explicitly review the action findings before approval.",
                    "RunSkeptic_decision": "VERIFY",
                }
            )

    return findings


def determine_status(findings: list[dict[str, Any]]) -> str:
    if any(item.get("severity") == "BLOCKER" for item in findings):
        return "REWORK_REQUIRED"
    if findings:
        return "APPROVAL_READY_WITH_ACTIONS"
    return "APPROVAL_READY"


def build_review(workspace: Path) -> dict[str, Any]:
    sync = workspace / ".specify" / "sync"
    manifest = load_json(sync / "speckit_input_manifest.json")
    queue = load_json(sync / "speckit_invocation_queue.json")
    constitution = load_json(sync / "constitution_update_plan.json")
    graph = load_json(sync / "feature_dependency_graph.json")
    usecase_map = load_json(sync / "hld_usecase_api_map.json")
    dossier_quality = load_json(sync / "hld_answer_dossier_quality_review.json")
    spec_list = load_json(sync / "hldspec_speckit_spec_list.json")

    findings = build_findings(manifest, graph, constitution, queue, usecase_map, dossier_quality, spec_list)
    status = determine_status(findings)

    features = [item for item in as_list(manifest.get("features")) if isinstance(item, dict)]
    roots = [item for item in features if not as_list(item.get("depends_on_features"))]
    first_feature = roots[0] if roots else (features[0] if features else {})

    return {
        "schema_version": 1,
        "status": status,
        "review_type": "SPECKIT_PREWORK_QUALITY_GATE",
        "RunSkeptic_method": {
            "flow": "GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN",
            "purpose": "Detect unclear architecture, weak decomposition, missing foundations, and user-confusing explanations before SpecKit invocation.",
            "decision_policy": "BLOCKER findings require rebuild; ACTION findings require explicit judge explanation before human approval.",
        },
        "case_to_present": {
            "constitution_case": {
                "claim": "The constitution should protect HLD architecture before SpecKit creates feature artifacts.",
                "evidence": [rule.get("name", "") for rule in as_list(constitution.get("required_rules")) if isinstance(rule, dict)],
                "approval_question": "Does this constitution plan correctly protect the architecture before invoking SpecKit?",
            },
            "architecture_plan_case": {
                "claim": "Features should be built bottom-up from independent/common foundations to dependent user-facing behavior.",
                "bottom_up_order": as_list(graph.get("bottom_up_order")),
                "approval_question": "Does this dependency order make architectural sense?",
            },
            "first_feature_case": {
                "feature_id": first_feature.get("feature_id", ""),
                "feature_name": feature_name(first_feature) if first_feature else "",
                "why_first": (
                    "This feature has no dependencies and is therefore the first foundation/root feature."
                    if first_feature and not as_list(first_feature.get("depends_on_features"))
                    else "First feature was selected by fallback order because no dependency-free root was identified."
                ),
                "depends_on": as_list(first_feature.get("depends_on_features")) if first_feature else [],
            },
        },
        "affected_artifact_policy": {
            "if_human_changes_constitution": [
                "rebuild constitution_update_plan",
                "rebuild speckit_input_manifest if rules affect feature boundaries",
                "rebuild feature_dependency_graph if rules affect dependencies",
                "rebuild speckit_invocation_queue",
                "rerun this quality gate",
            ],
            "if_human_changes_dependency_order": [
                "rebuild feature_dependency_graph",
                "rebuild speckit_invocation_queue",
                "rerun this quality gate",
            ],
            "if_human_requests_decomposition": [
                "update working HLD or HLD-SPECS mapping",
                "rerun first_readonly",
                "regenerate SpecKit prework artifacts",
                "rerun this quality gate",
            ],
        },
        "findings": findings,
        "human_checkpoint": {
            "question": "Do you approve the constitution, architecture dependency plan, and first SpecKit feature order?",
            "options": [
                "APPROVE_PLAN",
                "MODIFY_PLAN",
                "DECOMPOSE_MORE",
                "FIX_CONSTITUTION",
                "REBUILD_DEPENDENCY_GRAPH",
            ],
            "human_decision": "TBD",
        },
    }


def render_md(review: dict[str, Any]) -> str:
    case = review["case_to_present"]
    lines = [
        "# SpecKit Prework Quality Review",
        "",
        "",
        "",
        f"Status: `{review['status']}`",
        f"Review type: `{review['review_type']}`",
        "",
        "## Where we are",
        "",
        "HLDspec has prepared SpecKit inputs but must not invoke SpecKit yet.",
        "",
        "The judge/orchestrator must present the constitution case, architecture/dependency case, and first-feature case to the human.",
        "",
        "## RunSkeptic review method",
        "",
        f"- flow: `{review['RunSkeptic_method']['flow']}`",
        f"- purpose: {review['RunSkeptic_method']['purpose']}",
        f"- decision policy: {review['RunSkeptic_method']['decision_policy']}",
        "",
        "## Constitution case",
        "",
        f"Claim: {case['constitution_case']['claim']}",
        "",
        "Evidence / proposed rules:",
    ]
    for item in case["constitution_case"]["evidence"]:
        lines.append(f"- {item}")
    lines += [
        "",
        f"Approval question: {case['constitution_case']['approval_question']}",
        "",
        "## Architecture and dependency case",
        "",
        f"Claim: {case['architecture_plan_case']['claim']}",
        "",
        "Bottom-up order:",
    ]
    for idx, item in enumerate(case["architecture_plan_case"]["bottom_up_order"], start=1):
        lines.append(f"{idx}. `{item}`")
    lines += [
        "",
        f"Approval question: {case['architecture_plan_case']['approval_question']}",
        "",
        "## First feature case",
        "",
        f"- feature: `{case['first_feature_case']['feature_id']}` - {case['first_feature_case']['feature_name']}",
        f"- why first: {case['first_feature_case']['why_first']}",
        f"- depends on: {', '.join(case['first_feature_case']['depends_on']) or 'none'}",
        "",
        "## Skeptic findings",
        "",
    ]

    if not review["findings"]:
        lines.append("No blocking or action findings.")
    for finding in review["findings"]:
        lines += [
            f"### {finding['id']} - {finding['area']}",
            "",
            f"- severity: `{finding['severity']}`",
            f"- RunSkeptic decision: `{finding['RunSkeptic_decision']}`",
            f"- finding: {finding['finding']}",
            f"- recommendation: {finding['recommendation']}",
            "",
        ]

    lines += [
        "## If you give feedback",
        "",
        "The judge/orchestrator must rebuild affected artifacts, not patch only one file.",
        "",
        "### Feedback impact rules",
        "",
    ]
    for key, actions in review["affected_artifact_policy"].items():
        lines.append(f"#### {key}")
        for action in actions:
            lines.append(f"- {action}")
        lines.append("")

    checkpoint = review["human_checkpoint"]
    lines += [
        "## Human checkpoint",
        "",
        checkpoint["question"],
        "",
        "Options:",
    ]
    for option in checkpoint["options"]:
        lines.append(f"- {option}")
    lines += [
        "",
        "Human decision: `TBD`",
        "",
    ]

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build quality gate for SpecKit prework artifacts.")
    parser.add_argument("workspace")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    out = workspace / ".specify" / "sync"
    out.mkdir(parents=True, exist_ok=True)

    review = build_review(workspace)
    json_path = out / "speckit_prework_quality_review.json"
    md_path = out / "speckit_prework_quality_review.md"

    json_path.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_md(review), encoding="utf-8")

    print("SpecKit prework quality review generated:")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    print(f"- status: {review['status']}")
    print(f"- findings: {len(review['findings'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
