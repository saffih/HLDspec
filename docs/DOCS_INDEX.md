# HLDspec Docs Index

Use this page to choose the current doc before reading historical material.

## Start here

| Doc | Purpose |
|---|---|
| [`../README.md`](../README.md) | Conceptual front door: what HLDspec does, the three journeys, and the normal workflow. |
| [`HLDSPEC_TERMINOLOGY_AND_FLOW.md`](HLDSPEC_TERMINOLOGY_AND_FLOW.md) | Authoritative canonical architecture, terminology, ownership boundaries, full flow, and SpecKit Run Card. Wins on conflicts. |
| [`../AGENTS.md`](../AGENTS.md) | Repo agent bootstrap and HLDspec invocation rules. |
| [`../TASKS.md`](../TASKS.md) | Living task tracker for current HLDspec repo work. |

## Active reference

| Doc | Purpose |
|---|---|
| [`SPECKIT_SLICE_CONTROL.md`](SPECKIT_SLICE_CONTROL.md) | Technical slice-control model: one full SpecKit flow, then bounded implementation slices. |
| [`SPECKIT_PROXY_PROTOCOL.md`](SPECKIT_PROXY_PROTOCOL.md) | HLDspec-to-SpecKit handoff protocol and proxy responsibilities. |
| [`HLDSPEC_GAP_HANDOFF_TEMPLATE.md`](HLDSPEC_GAP_HANDOFF_TEMPLATE.md) | Status/handoff template for continuation evidence and next safe action; not architecture truth. |
| [`HLDSPEC_ARTIFACT_CONTRACT_STYLE.md`](HLDSPEC_ARTIFACT_CONTRACT_STYLE.md) | Standard contract shape for prompts, reports, handoffs, and slice instructions. |
| [`HLDSPEC_ARCHITECTURE_README.md`](HLDSPEC_ARCHITECTURE_README.md) | Architecture README for source-package model, SpecKit handoff, generated artifacts, gates, and tests. |
| [`ARCHITECTURE_V2.md`](ARCHITECTURE_V2.md) | V2 code-level architecture: machines, contracts, and pipeline. |
| [`CANONICAL_FLOW.md`](CANONICAL_FLOW.md) | Current control-flow reference, subordinate to the canonical terminology doc. |
| [`HLDSPEC_DEVELOPMENT_HANDOFF.md`](HLDSPEC_DEVELOPMENT_HANDOFF.md) | Canonical repo-development handoff protocol. |
| [`HLDSPEC_DEVELOPMENT_BACKLOG.md`](HLDSPEC_DEVELOPMENT_BACKLOG.md) | Durable backlog for unfinished HLDspec repo-development work and open decisions. |
| [`HLDSPEC_USE_CASES_AND_API.md`](HLDSPEC_USE_CASES_AND_API.md) | Product use-case catalog and API scenarios. |
| [`HLDSPEC_V2_AGENT_ROLES.md`](HLDSPEC_V2_AGENT_ROLES.md) | Subagent and reviewer role definitions. |
| [`JUDGE_LED_REVIEW_PROTOCOL.md`](JUDGE_LED_REVIEW_PROTOCOL.md) | Judge-led human review protocol. |
| [`RUNSKEPTIC_EVIDENCE_QUALITY.md`](RUNSKEPTIC_EVIDENCE_QUALITY.md) | RunSkeptic evidence field contract. |
| [`CONSTITUTION_RULE_QUALITY.md`](CONSTITUTION_RULE_QUALITY.md) | Constitution rule quality gate. |
| [`AGENT_ARTIFACT_HYGIENE.md`](AGENT_ARTIFACT_HYGIENE.md) | Policy for ad hoc docs, scratch output, target artifacts, and cleanup metadata. |
| [`CONTEXT_TAILORING_PROTOCOL.md`](CONTEXT_TAILORING_PROTOCOL.md) | Context tailoring for subagents. |
| [`HLDSPEC_V2_HANDOFF_DOCS.md`](HLDSPEC_V2_HANDOFF_DOCS.md) | Handoff doc specification. |
| [`HLDSPEC_STABILITY_ARCHITECTURE.md`](HLDSPEC_STABILITY_ARCHITECTURE.md) | Stability architecture principles and next small hardening slices. |
| [`BACKEND_TECHNOLOGY_RECOMMENDATION.md`](BACKEND_TECHNOLOGY_RECOMMENDATION.md) | Approved backend toolbox defaults and upgrade triggers. |
| [`ENGINEERING_TOOLBOX.md`](ENGINEERING_TOOLBOX.md) | Engineering Toolbox terminology, guidance levels, and enforcement loop. |
| [`HLDSPEC_RUNTIME_DOCUMENT_USAGE.md`](HLDSPEC_RUNTIME_DOCUMENT_USAGE.md) | Runtime rules for using guidance docs during HLDspec runs. |
| [`SOFTWARE_DESIGN_PRINCIPLES.md`](SOFTWARE_DESIGN_PRINCIPLES.md) | Reusable software design principles for HLD generation, prompts, RunSkeptic, and context economy. |
| [`HLD_TO_TARGET_WORKSPACE.md`](HLD_TO_TARGET_WORKSPACE.md) | Target workspace model and HLD evidence layout. |
| [`CONSTITUTION_GENERATION.md`](CONSTITUTION_GENERATION.md) | Principle-level target constitution generation rules. |
| [`SPECKIT_DELEGATION_PROMPTS.md`](SPECKIT_DELEGATION_PROMPTS.md) | Generated prompts for SpecKit phase delegation. |
| [`MEDIATOR_PROMPT_PROTOCOL.md`](MEDIATOR_PROMPT_PROTOCOL.md) | Mediator prompt protocol for Devin, Claude, and Codex target agents. |
| [`TEST_STRATEGY_V2.md`](TEST_STRATEGY_V2.md) | Test strategy and conventions. |
| [`SMOKE_SCENARIOS.md`](SMOKE_SCENARIOS.md) | Deterministic smoke scenarios and output contracts. |
| [`REFACTOR_PROGRAM.md`](REFACTOR_PROGRAM.md) | Refactor program status and outstanding work. |

## Runtime entrypoints

| Script / Module | Role |
|---|---|
| `scripts/hldspec_v2.py` | CLI entry point. |
| `scripts/hldspec_run.sh` | Canonical run entry for the full pipeline. |
| `scripts/project_first_run.sh` | First-time workspace setup. |
| `scripts/project_continue.sh` | Resume and status check. |
| `scripts/first_run_readonly.sh` | Bootstrap read-only analysis. |
| `scripts/hldspec_agent_session.py` | Public agent-first facade. |
| `hldspec/machines/project.py` | Orchestrator machine. |
| `hldspec/skeptic_schema.py` | RunSkeptic canonical finding schema. |

## Archive / Historical

These docs are historical records only. They are not updated and should not be
used as active references.

| Doc | What it was |
|---|---|
| [`archive/HLDSPEC_RUNSKEPTIC_*.md`](archive/) | Point-in-time RunSkeptic cycle reviews. |
| [`archive/HLDSPEC_IMPLEMENTATION_TODO.md`](archive/HLDSPEC_IMPLEMENTATION_TODO.md) | Historical TODO, superseded by `TASKS.md`. |
| [`archive/HLDSPEC_V2_APPLY_DEBUG.md`](archive/HLDSPEC_V2_APPLY_DEBUG.md) | Debug session notes. |
| [`archive/CHUNKED_AGENT_PROTOCOL.md`](archive/CHUNKED_AGENT_PROTOCOL.md) | Deprecated agent protocol. |
| [`archive/EXTERNAL_AGENT_PROMPT.md`](archive/EXTERNAL_AGENT_PROMPT.md) | Deprecated agent prompt. |
| [`archive/ARCHITECTURE_ENHANCEMENT_OPTIONS.md`](archive/ARCHITECTURE_ENHANCEMENT_OPTIONS.md) | Enhancement options planning doc, superseded by `HLDSPEC_STABILITY_ARCHITECTURE.md`. |
| [`archive/CONTEXT_BUDGET.md`](archive/CONTEXT_BUDGET.md) | Historical context budget protocol. |
| [`archive/FIRST_RUN.md`](archive/FIRST_RUN.md) | Historical first-run walkthrough. |
| [`archive/TARGET_SPEC_CONTEXT.md`](archive/TARGET_SPEC_CONTEXT.md) | Historical HLD evidence to target-spec context rules. |
