from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ArtifactContract:
    artifact_name: str
    schema_version: int
    producer: str            # script or machine name
    consumers: list[str]     # script/machine names
    required_fields: list[str]
    optional_fields: list[str] = field(default_factory=list)
    input_artifacts: list[str] = field(default_factory=list)
    output_artifacts: list[str] = field(default_factory=list)
    notes: str = ""


ARTIFACT_CONTRACTS: dict[str, ArtifactContract] = {
    "spec_build_plan.json": ArtifactContract(
        artifact_name="spec_build_plan.json",
        schema_version=1,
        producer="build_spec_build_plan.py",
        consumers=["SpecBuildPlanMachine", "enrich_spec_build_plan_with_answer_context.py", "build_speckit_prework_plan.py"],
        required_fields=["plan_quality", "planned_specs"],
        optional_fields=["enriched_at"],
        input_artifacts=["hld_usecase_api_map.json"],
        output_artifacts=[],
    ),
    "speckit_invocation_queue.json": ArtifactContract(
        artifact_name="speckit_invocation_queue.json",
        schema_version=1,
        producer="build_speckit_prework_plan.py",
        consumers=["SpecKitExecutionMachine"],
        required_fields=["items"],
        optional_fields=[],
        input_artifacts=["spec_build_plan.json", "feature_dependency_graph.json"],
        output_artifacts=[],
    ),
    "speckit_prework_quality_review.json": ArtifactContract(
        artifact_name="speckit_prework_quality_review.json",
        schema_version=1,
        producer="build_speckit_prework_quality_review.py",
        consumers=["SpeckitPreworkMachine"],
        required_fields=["status", "findings"],
        optional_fields=[],
        input_artifacts=["speckit_invocation_queue.json", "constitution_update_plan.json"],
        output_artifacts=[],
    ),
    "hld_conversion_decision_queue.json": ArtifactContract(
        artifact_name="hld_conversion_decision_queue.json",
        schema_version=1,
        producer="build_hld_conversion_decision_queue.py",
        consumers=["RawHldConversionMachine", "ApplyHldConversionMachine"],
        required_fields=["questions"],
        optional_fields=[],
        input_artifacts=["HLD.raw.md"],
        output_artifacts=[],
    ),
    "speckit_execution_state.json": ArtifactContract(
        artifact_name="speckit_execution_state.json",
        schema_version=1,
        producer="SpecKitExecutionMachine",
        consumers=["SpecKitExecutionMachine"],
        required_fields=[],  # flexible state bag
        optional_fields=["constitution_approved", "active_feature_index", "active_phase", "all_complete"],
        input_artifacts=[],
        output_artifacts=[],
        notes="State persistence artifact — read and written by same machine",
    ),
    "hldspec_state.json": ArtifactContract(
        artifact_name="hldspec_state.json",
        schema_version=1,
        producer="build_hldspec_state.py",
        consumers=["operator"],
        required_fields=["current_stage", "current_checkpoint", "next_allowed_actions"],
        optional_fields=["blocking_questions", "stale_artifact_warnings", "plan_summary", "notes"],
        input_artifacts=["spec_build_plan.json", "speckit_prework_quality_review.json"],
        output_artifacts=[],
    ),
}


def validate_contract(artifact_name: str, data: dict[str, Any]) -> list[str]:
    """Return list of violation strings for data against its contract."""
    contract = ARTIFACT_CONTRACTS.get(artifact_name)
    if contract is None:
        return []  # No contract registered — not a violation
    missing = [f for f in contract.required_fields if f not in data]
    return [f"{artifact_name}: missing required field '{f}'" for f in missing]


def registered_artifacts() -> list[str]:
    return list(ARTIFACT_CONTRACTS.keys())
