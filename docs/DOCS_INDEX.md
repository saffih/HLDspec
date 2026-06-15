# HLDspec Docs Index

Authoritative reference vs active guidance vs archive/history. When in doubt, start here.

---

## Start here

| Doc | Purpose |
|---|---|
| [`../README.md`](../README.md) | Conceptual front door: what HLDspec does, the three journeys, and the normal workflow. |
| [`HLDSPEC_TERMINOLOGY_AND_FLOW.md`](HLDSPEC_TERMINOLOGY_AND_FLOW.md) | Authoritative canonical architecture, terminology, ownership boundaries, full flow, and SpecKit Run Card. Wins on conflicts. The canonical terminology/command-surface source. |
| [`ARCHITECTURE_LAYERS.md`](ARCHITECTURE_LAYERS.md) | The product/layer map: product purpose, three journeys, implementation modes, the seven product layers, and current/intended/future honesty. |
| [`THREE_JOURNEYS.md`](THREE_JOURNEYS.md) | Product framing: the three journeys with typed handoffs, the "SpecKit is one helper" re-scope of Journey 3, the minimal vocabulary, and the Prompt 1→2→3 contract-hardening sequence. |
| [`JOURNEY1_SDD_READY_GATE.md`](JOURNEY1_SDD_READY_GATE.md) | Journey 1 contract: the testable SDD-ready HLD gate — definition, required/optional sections, allowed vs blocker ambiguity, PASS/ACTION/BLOCKED bound to `HLD_READY`/`HLD_READY_WITH_ACTIONS`/`HLD_BLOCKED`, evidence for PASS, RunSkeptic questions, and validation strategy. |
| [`REPO_MIGRATION_PLAN.md`](REPO_MIGRATION_PLAN.md) | The phased change plan: top-level classification and the migration phases (no broad moves first; tests before moves; rollback per phase). |
| [`../AGENTS.md`](../AGENTS.md) | Repo agent bootstrap and HLDspec invocation rules. |
| [`SPECKIT_DRIVING_MODELS.md`](SPECKIT_DRIVING_MODELS.md) | The two SpecKit driving models (HLD pipeline vs ad-hoc in-target) and the canonical ritual chain they share, bound by an anti-drift test. |
| [`SPECKIT_SLICE_CONTROL.md`](SPECKIT_SLICE_CONTROL.md) | Technical slice-control model and generated slice artifact contract. |
| [`SPECKIT_PROXY_PROTOCOL.md`](SPECKIT_PROXY_PROTOCOL.md) | HLDspec-to-SpecKit handoff and proxy protocol. |
| [`SMOKE_SCENARIOS.md`](SMOKE_SCENARIOS.md) | Deterministic smoke scenarios, commands, target layout, and PASS/FAIL output contract. |
| [`REPO_LAYOUT.md`](REPO_LAYOUT.md) | Compact map of root files: active V2 source, shared parser, V1 pipeline, root docs, and the three test roots. |
| [`PRODUCT_READINESS.md`](PRODUCT_READINESS.md) | Readiness scorecard: tiers, gates, current status, evidence, path-safety summary, and what independent RunSkeptic must verify. |

---

## Active reference

| Doc | Purpose |
|---|---|
| [`HLDSPEC_ARTIFACT_CONTRACT_STYLE.md`](HLDSPEC_ARTIFACT_CONTRACT_STYLE.md) | Standard interface-contract shape for handoffs, prompts, reports, gap handoffs, and slice execution artifacts. |
| [`ENGINEERING_TOOLBOX.md`](ENGINEERING_TOOLBOX.md) | Durable engineering doctrine for constitution candidates, preferred choice selection, clean-software cards, and stage-safety guidance. |
| [`ANTI_DRIFT_CONTRACTS.md`](ANTI_DRIFT_CONTRACTS.md) | Non-droppable product, ownership, slice/mediator, and engineering-toolbox contracts that future changes must preserve. |
| [`HLDSPEC_GAP_HANDOFF_TEMPLATE.md`](HLDSPEC_GAP_HANDOFF_TEMPLATE.md) | Status handoff template for gaps, dirty state, next patch, and tests actually run. Not architecture truth. |
| [`HLDSPEC_DEVELOPMENT_HANDOFF.md`](HLDSPEC_DEVELOPMENT_HANDOFF.md) | Development handoff protocol for moving HLDspec repo work between models/agents/sessions. |
| [`HLDSPEC_DEVELOPMENT_BACKLOG.md`](HLDSPEC_DEVELOPMENT_BACKLOG.md) | Durable backlog of unfinished repo-development work and open design decisions. |
| [`TEST_STRATEGY_V2.md`](TEST_STRATEGY_V2.md) | Test strategy and conventions. |
| [`MEDIATOR_PROMPT_PROTOCOL.md`](MEDIATOR_PROMPT_PROTOCOL.md) | Mediator prompt protocol for Devin/Claude/Codex target agents. |
| [`CANONICAL_FLOW.md`](CANONICAL_FLOW.md) | Canonical pipeline flow reference. |
| [`ARCHITECTURE_V2.md`](ARCHITECTURE_V2.md) | V2 architecture: machines, contracts, and pipeline. |
| [`USER_RUN_MODEL.md`](USER_RUN_MODEL.md) | Simple user workflow over the public command surface; defers to `HLDSPEC_TERMINOLOGY_AND_FLOW.md` for the canonical command list. |
| [`AGENT_FIRST_PRODUCT_MODEL.md`](AGENT_FIRST_PRODUCT_MODEL.md) | Agent-first product model: users start sessions; scripts are tools. |
| [`RUNSKEPTIC_EVIDENCE_QUALITY.md`](RUNSKEPTIC_EVIDENCE_QUALITY.md) | RunSkeptic evidence field contract. |
| [`CONTEXT_TAILORING_PROTOCOL.md`](CONTEXT_TAILORING_PROTOCOL.md) | Context tailoring for subagents. |
| [`AGENT_ARTIFACT_HYGIENE.md`](AGENT_ARTIFACT_HYGIENE.md) | Policy for ad hoc docs, archive records, scratch output, target artifacts, and cleanup metadata. |

---

## Runtime Entry Points

| Script / Module | Role |
|---|---|
| `scripts/hldspec_agent_session.py` | Current public facade implementation: start/status/review/continue/diff/doctor/speckit-doctor/operator-state (alias speckit-state)/git-lifecycle. This is the only current product command surface listed here. |
| `scripts/hldspec_smoke_slice_e2e.py` | Production smoke scenario for source package, mirror, anchors, slice artifacts, and optional tmux visibility. |
| `scripts/hldspec_v2.py` | Compatibility/debug V2 CLI entry point. Do not advertise as the current user-facing product surface. |
| `scripts/hldspec_run.sh` | Legacy/debug full-pipeline runner. It is not the canonical product entry point; use the public facade above for product behavior. |
| `scripts/project_first_run.sh` | Internal/compatibility first-time workspace setup runner used by the facade and tests. |
| `scripts/project_continue.sh` | Internal/compatibility resume/status runner used by ProjectMachine flows. |
| `scripts/first_run_readonly.sh` | Internal bootstrap read-only analysis runner. Maintainer/debug surface, not a user-facing product command. |
| `hldspec/machines/project.py` | Orchestrator machine. |
| `hldspec/skeptic_schema.py` | RunSkeptic canonical finding schema. |

Rule: if this section conflicts with `HLDSPEC_TERMINOLOGY_AND_FLOW.md`, the
terminology-and-flow command surface wins. Direct scripts may appear in tests,
debug docs, and compatibility docs, but they must not be presented as the current
product workflow.

---

## Archive / historical

Historical docs are point-in-time RunSkeptic reviews and superseded design docs. They are not active references unless a current doc points to them explicitly.

Full archive contents: [`docs/archive/`](archive/)
