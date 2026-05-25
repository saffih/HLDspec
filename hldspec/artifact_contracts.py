from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Input location constants
SYNC_LOCAL = "sync"           # .specify/sync/<name>
WORKSPACE_ROOT = "workspace"  # <workspace>/<name>  (e.g. HLD.raw.md)


@dataclass
class ArtifactInput:
    """Declares a single input artifact with its location root."""
    name: str
    location: str = SYNC_LOCAL   # SYNC_LOCAL | WORKSPACE_ROOT


@dataclass
class ArtifactContract:
    artifact_name: str
    schema_version: int
    producer: str            # script or machine name
    consumers: list[str]     # script/machine names
    required_fields: list[str]
    optional_fields: list[str] = field(default_factory=list)
    input_artifacts: list[str] = field(default_factory=list)   # legacy: sync-local names
    input_specs: list[ArtifactInput] = field(default_factory=list)  # typed, multi-root
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
        input_artifacts=[],  # HLD.raw.md is workspace-root; use input_specs
        input_specs=[ArtifactInput(name="HLD.raw.md", location=WORKSPACE_ROOT)],
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


def stale_registered_artifacts(sync: Path, workspace: Path | None = None) -> list[str]:
    """Return registered artifacts that are stale relative to their declared inputs.

    Checks both legacy input_artifacts (sync-local) and typed input_specs
    which may be SYNC_LOCAL or WORKSPACE_ROOT.

    Args:
        sync: path to .specify/sync directory
        workspace: path to workspace root; required to resolve WORKSPACE_ROOT inputs
    """
    blockers: list[str] = []
    for artifact_name, contract in ARTIFACT_CONTRACTS.items():
        has_inputs = bool(contract.input_artifacts or contract.input_specs)
        if not has_inputs:
            continue
        output = sync / artifact_name
        if not output.exists():
            continue
        output_mtime = output.stat().st_mtime
        newer: list[str] = []

        # Legacy sync-local inputs
        for inp in contract.input_artifacts:
            p = sync / inp
            if p.exists() and p.stat().st_mtime > output_mtime:
                newer.append(inp)

        # Typed inputs (may be workspace-root)
        for inp_spec in contract.input_specs:
            if inp_spec.location == WORKSPACE_ROOT:
                if workspace is None:
                    continue  # can't check without workspace path
                p = workspace / inp_spec.name
            else:
                p = sync / inp_spec.name
            if p.exists() and p.stat().st_mtime > output_mtime:
                newer.append(inp_spec.name)

        if newer:
            blockers.append(
                f"{artifact_name} is stale: newer input(s): {', '.join(newer)}"
            )
    return blockers
