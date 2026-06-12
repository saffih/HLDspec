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
        optional_fields=["runskeptic_status", "run_skeptic_status", "skeptic_status"],
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
    "hld_cross_examination.json": ArtifactContract(
        artifact_name="hld_cross_examination.json",
        schema_version=1,
        producer="check_hld_readiness",
        consumers=["hld_readiness_check.json", "HLDspec Judge Orchestrator"],
        required_fields=["schema_version", "status", "examined_items", "grouped_questions"],
        optional_fields=[
            "source_hld",
            "reason_kind_values",
            "item_status_values",
            "summary",
            "polite_clarification_prompt",
        ],
        input_specs=[ArtifactInput(name="HLD.md", location=WORKSPACE_ROOT)],
        output_artifacts=["hld_readiness_check.json"],
        notes="Auxiliary reason trail for SDD readiness; does not replace or mutate the main HLD.",
    ),
    "hld_readiness_check.json": ArtifactContract(
        artifact_name="hld_readiness_check.json",
        schema_version=1,
        producer="check_hld_readiness",
        consumers=["ProjectMachine", "HLDspec Judge Orchestrator"],
        required_fields=["schema_version", "verdict", "blockers", "next_safe_action"],
        optional_fields=[
            "source_hld",
            "cross_examination_artifact",
            "grouped_questions",
            "accepted_risks",
            "revisit_triggers",
        ],
        input_artifacts=["hld_cross_examination.json"],
        output_artifacts=[],
        notes="Early HLD-readiness verdict; must stop before full SpecKit Preparation, Build Loop init, or SpecKit execution.",
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
    "speckit_execution_assessment.json": ArtifactContract(
        artifact_name="speckit_execution_assessment.json",
        schema_version=1,
        producer="speckit_execution_state.py",
        consumers=["operator-state", "hldspec_speckit_next.py"],
        required_fields=["schema_version", "status", "bundles"],
        optional_fields=["resume", "bundle_count", "speckit_root", "assessable"],
        input_artifacts=["speckit_bundle_queue.json", "speckit_invocation_queue.json"],
        output_artifacts=[],
        notes="Derived read-only progress assessment; must not overwrite SpecKitExecutionMachine state",
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
    "target_discovery_report.json": ArtifactContract(
        artifact_name="target_discovery_report.json",
        schema_version=1,
        producer="target_discovery.py",
        consumers=["status", "doctor", "operator-state", "continue"],
        required_fields=[
            "schema_version",
            "target",
            "classification",
            "trusted_hldspec_lineage",
            "blockers",
            "next_safe_action",
            "phase_ledger_status",
            "phase_ledger_safety",
            "phase_ledger",
        ],
        optional_fields=[
            "lineage_evidence",
            "existing_payload_paths",
            "specify_memory_exists",
            "spec_phase_artifacts_exist",
            "report_paths",
            "reports_written",
        ],
        output_artifacts=["phase_ledger.json"],
        notes="Read-only existing-sensitive greenfield discovery; must not run SpecKit, implement product code, or wipe target state.",
    ),
    "phase_ledger.json": ArtifactContract(
        artifact_name="phase_ledger.json",
        schema_version=1,
        producer="target_discovery.py",
        consumers=["target_discovery_report.json", "operator-state", "continue"],
        required_fields=[
            "schema_version",
            "target",
            "overall_status",
            "safety_status",
            "summary",
            "entries",
            "blockers",
        ],
        optional_fields=[],
        input_artifacts=["target_discovery_report.json"],
        output_artifacts=[],
        notes=(
            "Read-only phase wake ledger; file existence alone must not mean DONE. "
            "overall_status is lifecycle only; safety_status (PASS/ACTION/BLOCKED) gates continuation."
        ),
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
