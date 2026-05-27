"""SpecKit implementation slicing policy artifacts.

HLDspec keeps one complete HLD and one complete SpecKit specify/plan/tasks/analyze
flow. Implementation is then executed in controlled slices. This module renders the
HLDspec-owned context files that explain those slices to SpecKit runners and agents.
"""
from __future__ import annotations

import json
from copy import deepcopy

SCHEMA_VERSION = 1

IMPLEMENTATION_SLICING_POLICY_FILE = "implementation_slicing_policy.md"
IMPLEMENTATION_SLICES_FILE = "implementation_slices.json"
SLICE_TEST_POLICY_FILE = "slice_test_policy.md"
SPECKIT_SLICE_EXECUTION_PROMPT_FILE = "speckit_slice_execution_prompt.md"
ANCHOR_COVERAGE_SCHEMA_FILE = "anchor_coverage_schema.json"

SLICE_ORDER: tuple[str, ...] = (
    "FOUNDATION",
    "WALKING_SKELETON",
    "DOMAIN_MODEL",
    "CONTRACTS",
    "BUSINESS_LOGIC",
    "PERSISTENCE",
    "API",
    "CLI",
    "UI",
    "INTEGRATION_HARDENING",
)

DEFAULT_SLICES: tuple[dict, ...] = (
    {
        "name": "FOUNDATION",
        "purpose": "Create valid workspace, build/test commands, and source-package control.",
        "allowed_work": ["workspace setup", "build/test commands", "directory structure", "source mirror validation"],
        "forbidden_work": ["business behavior", "UI behavior", "database product schema"],
        "required_tests": ["build command runs", "test command runs", "source mirror is generated and valid"],
    },
    {
        "name": "WALKING_SKELETON",
        "purpose": "Create a minimal executable path through the app with placeholders.",
        "allowed_work": ["entry point", "empty boundaries", "health/smoke path", "dependency wiring"],
        "forbidden_work": ["real business rules", "full UI", "non-required persistence"],
        "required_tests": ["app starts", "smoke path passes", "invalid config fails clearly"],
    },
    {
        "name": "DOMAIN_MODEL",
        "purpose": "Define entities, value objects, statuses, domain errors, and pure invariants.",
        "allowed_work": ["entities", "value objects", "enums/statuses", "domain errors", "pure invariants"],
        "forbidden_work": ["database", "API", "CLI", "UI", "network"],
        "required_tests": ["entity tests", "value object tests", "negative invariant tests"],
    },
    {
        "name": "CONTRACTS",
        "purpose": "Define stable ports, DTOs, schemas, and external-facing contracts.",
        "allowed_work": ["ports/interfaces", "DTOs", "schemas", "events/messages", "repository contracts"],
        "forbidden_work": ["hidden business decisions", "adapter implementation unless fake/in-memory"],
        "required_tests": ["schema validation tests", "port contract tests", "invalid payload tests"],
    },
    {
        "name": "BUSINESS_LOGIC",
        "purpose": "Implement use cases, workflows, validation rules, and state transitions.",
        "allowed_work": ["use cases", "application services", "workflow tests", "domain/application tests"],
        "forbidden_work": ["controllers", "UI", "database migrations unless explicitly required"],
        "required_tests": ["focused use-case tests", "error-path tests", "prior domain and contract regression"],
    },
    {
        "name": "PERSISTENCE",
        "purpose": "Store and retrieve state through adapters that satisfy the contracts.",
        "allowed_work": ["database schema", "migrations", "repository adapters", "transactions", "persistence tests"],
        "forbidden_work": ["new business rules", "UI", "API behavior changes not required by contract"],
        "required_tests": ["migration from empty DB", "repository round-trip tests", "rollback/constraint tests"],
    },
    {
        "name": "API",
        "purpose": "Expose approved use cases through HTTP/RPC or equivalent service API.",
        "allowed_work": ["routes", "controllers", "request/response mapping", "API tests", "OpenAPI if required"],
        "forbidden_work": ["new business rules", "UI", "unapproved persistence changes"],
        "required_tests": ["route tests", "status code tests", "request validation tests", "error mapping tests"],
    },
    {
        "name": "CLI",
        "purpose": "Expose approved use cases through command-line commands.",
        "allowed_work": ["commands", "flags/arguments", "exit codes", "stdout/stderr behavior", "CLI tests"],
        "forbidden_work": ["new business rules", "UI", "unapproved API changes"],
        "required_tests": ["command parsing tests", "exit code tests", "stdout/stderr tests", "CLI integration tests"],
    },
    {
        "name": "UI",
        "purpose": "Expose approved user flows visually.",
        "allowed_work": ["screens", "components", "forms", "UI state", "accessibility checks", "E2E tests"],
        "forbidden_work": ["backend rule changes without approval", "new product behavior not anchored in HLD"],
        "required_tests": ["component tests", "form validation tests", "loading/empty/error state tests", "accessibility checks", "E2E flow tests"],
    },
    {
        "name": "INTEGRATION_HARDENING",
        "purpose": "Close release gaps and prove the product works as one system.",
        "allowed_work": ["full regression", "E2E tests", "security checks", "performance smoke", "docs", "release validation"],
        "forbidden_work": ["new scope", "uncited product behavior", "silent HLD truth changes"],
        "required_tests": ["full unit suite", "full integration suite", "full E2E suite", "lint/type/security checks where applicable"],
    },
)


def build_implementation_slices() -> dict:
    """Return the machine-readable slice policy."""
    return {
        "schema_version": SCHEMA_VERSION,
        "source_truth_rule": "One full HLD, one full SpecKit spec/plan/tasks/analyze cycle, many controlled implementation passes.",
        "canonical_flow": ["speckit.specify", "speckit.plan", "speckit.tasks", "speckit.analyze", "slice_controlled_implementation"],
        "implement_rule": "Do not run raw all-task implementation unless full implementation is explicitly approved.",
        "slices": deepcopy(list(DEFAULT_SLICES)),
    }


def render_implementation_slices_json() -> str:
    return json.dumps(build_implementation_slices(), indent=2, sort_keys=True) + "\n"


def render_implementation_slicing_policy() -> str:
    return """# Implementation Slicing Policy

## Core rule

HLDspec passes one complete product truth into SpecKit. SpecKit should create one complete specify output, one complete plan, one complete task graph, and one analyze pass. Implementation is then executed in controlled slices.

Do not split the HLD. Do not create partial source-truth specs. Do not omit requirements because they are deferred from the current implementation slice.

## Required SpecKit flow

1. Run specify from the full HLD-derived source input.
2. Run plan for the full product, organized by implementation slices and MVP path.
3. Run tasks for the full product, tagging every task with a slice, dependencies, HLD anchors, and tests.
4. Run analyze before implementation to verify coverage, dependencies, anchors, and test completeness.
5. Implement only the selected slice or selected task IDs, then stop.

## Slice completion rule

A slice is complete only when focused tests pass, prior-slice regression passes, anchor coverage is updated, no uncited product behavior is added, and a phase report is written.

## Raw implementation rule

Do not run raw all-task implementation unless the current gate explicitly approves full implementation. Normal operation is slice-controlled implementation.
"""


def render_slice_test_policy() -> str:
    lines = [
        "# Slice Test Policy",
        "",
        "Every implementation slice must define focused validation and prior-slice regression.",
        "",
        "Universal requirements:",
        "",
        "- Every product task must cite HLD anchors unless it is mechanical foundation work.",
        "- Every implementation task must include a focused test or deterministic structural check.",
        "- Every slice must rerun tests for all previously completed slices.",
        "- No HLD anchor may be marked implemented without test evidence or explicit human-approved exception.",
        "- A slice must stop after writing phase_report.json and anchor_coverage.json.",
        "",
        "## Slice-specific minimums",
        "",
    ]
    for item in DEFAULT_SLICES:
        lines.append(f"### {item['name']}")
        lines.append("")
        lines.append(f"Purpose: {item['purpose']}")
        lines.append("")
        lines.append("Required tests/checks:")
        for test in item["required_tests"]:
            lines.append(f"- {test}")
        lines.append("")
    return "\n".join(lines)


def render_speckit_slice_execution_prompt() -> str:
    return """# SpecKit Slice Execution Prompt

Use this prompt only after specify, plan, tasks, and analyze have completed and the relevant implementation gate is approved.

## Required reads

Before acting, read:

- .specify/source/HLD.md
- .specify/source/hld_reference_map.json
- .specify/source/speckit_single_spec_input.md
- .specify/source/implementation_slicing_policy.md
- .specify/source/implementation_slices.json
- .specify/source/slice_test_policy.md
- tasks.md
- plan.md

## Execution command

Implement only the selected slice.

Selected slice: <SLICE_NAME>
Allowed task IDs: <TASK_IDS>
Allowed files: <ALLOWED_FILES>
Forbidden files: <FORBIDDEN_FILES>

Rules:

- Do not implement tasks outside the selected slice.
- Do not add product behavior without HLD anchor citation.
- Do not rewrite product truth.
- Run focused tests for this slice.
- Rerun prior-slice regression tests.
- Write phase_report.json.
- Write anchor_coverage.json.
- Stop after reporting blockers or PASS.
"""


def render_anchor_coverage_schema() -> str:
    schema = {
        "schema_version": SCHEMA_VERSION,
        "type": "object",
        "required": ["phase", "anchors"],
        "properties": {
            "phase": {"type": "string"},
            "anchors": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "required": ["status", "evidence"],
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["implemented", "partially_implemented", "deferred", "blocked", "not_applicable"],
                        },
                        "evidence": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
        },
    }
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def build_implementation_slicing_artifacts() -> dict[str, str]:
    return {
        IMPLEMENTATION_SLICING_POLICY_FILE: render_implementation_slicing_policy(),
        IMPLEMENTATION_SLICES_FILE: render_implementation_slices_json(),
        SLICE_TEST_POLICY_FILE: render_slice_test_policy(),
        SPECKIT_SLICE_EXECUTION_PROMPT_FILE: render_speckit_slice_execution_prompt(),
        ANCHOR_COVERAGE_SCHEMA_FILE: render_anchor_coverage_schema(),
    }
