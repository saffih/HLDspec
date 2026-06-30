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
| [`JOURNEY0_BROWNFIELD_DISCOVERY.md`](JOURNEY0_BROWNFIELD_DISCOVERY.md) | Journey 0 (product-direction/proposal, not yet gated): the pre-HLD brownfield discovery / HLD gap-assessment on-ramp that feeds Journey 1 — read-only evidence, gap routing, evidence labels (OBSERVED/INFERRED/UNKNOWN/CONFLICT/PRODUCT_DECISION_REQUIRED), the artifact set, and hard non-goals. Not a fourth journey; does not lift the brownfield-adoption restriction. |
| [`JOURNEY1_SDD_READY_GATE.md`](JOURNEY1_SDD_READY_GATE.md) | Journey 1 contract: the testable SDD-ready HLD gate — definition, required/optional sections, allowed vs blocker ambiguity, PASS/ACTION/BLOCKED bound to `HLD_READY`/`HLD_READY_WITH_ACTIONS`/`HLD_BLOCKED`, evidence for PASS, RunSkeptic questions, and validation strategy. |
| [`JOURNEY2_PACKAGE_CONTRACT.md`](JOURNEY2_PACKAGE_CONTRACT.md) | Journey 2 contract: the target package (= `source_package/`) — file schema, feature/spec-input/constitution sub-schemas, anchor-integrity validation, evidence-based vs must-not-invent rules, PASS/ACTION/BLOCKED bound to `SOURCE_PACKAGE_APPROVAL_GATE`, and the not-yet-emitted helper-recommendations seam. |
| [`JOURNEY2_INQUIRY_LEDGER_CONTRACT.md`](JOURNEY2_INQUIRY_LEDGER_CONTRACT.md) | Journey 2 inquiry/gap ledger and lens registry contract: epistemic state artifacts (`inquiry_ledger.json`, `gap_register.json`, advisory views), question lifecycle states (OPEN/ESCALATED/ASSUMED/…), gap types and severity (BLOCKER/WARNING/NOTE), lens registry concept (DOMAIN/ARCHITECTURE/QUALITY/TOOL_HELPER lenses separate from helper registry), binding model (HLD anchors → slices), gate integration, invariants, migration, and future tests. |
| [`JOURNEY2_SDD_COMPLETENESS_GATE.md`](JOURNEY2_SDD_COMPLETENESS_GATE.md) | Journey 2 product direction: the HLD Coverage Ledger / SDD Completeness Gate — HLD-item→SDD-section traceability, coverage statuses, research/clarification policies, and gate rules that block on `NOT_COVERED` items. Enriches `SOURCE_PACKAGE_APPROVAL_GATE` with a coverage dimension. Docs-only — no implementation. |
| [`JOURNEY2_READINESS_GATE_INVENTORY.md`](JOURNEY2_READINESS_GATE_INVENTORY.md) | Journey 2 readiness gate inventory: maps enforceable-now blockers (structural validation + `SOURCE_PACKAGE_APPROVAL_GATE`) vs defined-but-not-wired contracts (coverage ledger, gap ledger, inquiry ledger), existing artifacts and tests, and the smallest next implementation slice. Discovery only. |
| [`JOURNEY3_HELPER_CONTRACT.md`](JOURNEY3_HELPER_CONTRACT.md) | Journey 3 contract: consume the PASSed package, install a selected helper, guide the targeteer to completion — `HelperContract`, authority levels (GUIDE_ONLY/PROPOSE_COMMAND default), CompletionMap over the `next_feature_readiness` phases, the existing run-card runtime reclassified as `helper_id: speckit`, the `helper_recommendations` seam, and PASS/ACTION/BLOCKED. |
| [`HELPER_BOOTSTRAP_CONTRACT.md`](HELPER_BOOTSTRAP_CONTRACT.md) | Generic Helper Bootstrap contract: first-contact intake for unknown tools/skills → candidate `HelperContract` + `NextActionPacket`. Lifecycle states (UNKNOWN_TOOL → OPERATIONAL_HELPER), capability probes, intake questions, improper-use refusal statuses, authority-level caps, target-local layout (future), and PASS/ACTION/BLOCKED. |
| [`TOOLCHAIN_DRIVER_CONTRACT.md`](TOOLCHAIN_DRIVER_CONTRACT.md) | General Toolchain Driver v0 contract: Driver vs Helper, driver actor/authority vocabulary, read-only reporting scope, installed-runtime identity checks, and no-hidden-mutation boundaries. |
| [`TOOLCHAIN_DRIVER_BOUNDARY.md`](TOOLCHAIN_DRIVER_BOUNDARY.md) | Toolchain Driver Boundary contract: ownership zones (HLDspec-owned / adapter-mirror / read-only evidence / tool-owned-forbidden / ambiguous-escalate) backing `hldspec/toolchain_driver_boundary.py`, the SpecKit driver path, the `helper_selection.json` seam (`hldspec/helper_selection.py`), the ISG Governance future-toolchain seam, and the SourceBinding-prerequisite bridge table. |
| [`DRIVER_KISS_TDD_TRIAGE.md`](DRIVER_KISS_TDD_TRIAGE.md) | Driver triage contract: KISS + TDD defaults, current-evidence complexity rule, documentation-only validation, smallest-slice discipline, and human-owned protected approvals. |
| [`SPECKIT_HELPER_EXECUTION_CONTRACT.md`](SPECKIT_HELPER_EXECUTION_CONTRACT.md) | Contract-only future SpecKit helper gate: phase receipts, fail-closed transition and availability rules, human approval boundary, bypass detection, and canonical-sequence reconciliation before runtime adoption. |
| [`FIRST_LIVE_E2E_PROOF.md`](FIRST_LIVE_E2E_PROOF.md) | Supporting architectural evidence record for the first bounded Opus live proof: exact fixture scope, command identity, authority boundary, smoke limits, and unproven claims. |
| [`DRIVER_EVALUATION_LOOP_RESEARCH.md`](DRIVER_EVALUATION_LOOP_RESEARCH.md) | Supporting research record for the future Driver Evaluation Loop: role and authority separation, candidate checkpoints, trade-offs, and explicitly unimplemented follow-ups. |
| [`REPO_MIGRATION_PLAN.md`](REPO_MIGRATION_PLAN.md) | The phased change plan: top-level classification and the migration phases (no broad moves first; tests before moves; rollback per phase). |
| [`../AGENTS.md`](../AGENTS.md) | Repo agent bootstrap and HLDspec invocation rules. |
| [`SPECKIT_DRIVING_MODELS.md`](SPECKIT_DRIVING_MODELS.md) | The two SpecKit driving models (HLD pipeline vs ad-hoc in-target) and the canonical ritual chain they share, bound by an anti-drift test. |
| [`SPECKIT_SLICE_CONTROL.md`](SPECKIT_SLICE_CONTROL.md) | Technical slice-control model and generated slice artifact contract. |
| [`SPECKIT_PROXY_PROTOCOL.md`](SPECKIT_PROXY_PROTOCOL.md) | HLDspec-to-SpecKit handoff and proxy protocol. |
| [`SMOKE_SCENARIOS.md`](SMOKE_SCENARIOS.md) | Deterministic smoke scenarios, commands, target layout, and PASS/FAIL output contract. |
| [`REPO_LAYOUT.md`](REPO_LAYOUT.md) | Compact map of root files: active V2 source, shared parser, V1 pipeline, root docs, and the three test roots. |
| [`PRODUCT_READINESS.md`](PRODUCT_READINESS.md) | Readiness scorecard: tiers, gates, current status, evidence, path-safety summary, and what independent RunSkeptic must verify. |
| [`HLDSPEC_CURRENT_STATE_CHECKPOINT.md`](HLDSPEC_CURRENT_STATE_CHECKPOINT.md) | Current-state checkpoint after PR #53/#54: what is on main, what is not implemented, candidate next tracks. |
| [`CONTEXT_SAFETY_AND_GAP_CONTINUITY.md`](CONTEXT_SAFETY_AND_GAP_CONTINUITY.md) | Doctrine: context safety as a correctness requirement, context failure modes (hard limits, dilution, scope explosion), context isolation, bounded decomposition rules, validation-first decomposition, atomic-task criteria, gap continuity across session/handoff boundaries, and future persisted-artifact roadmap. Docs-only — no runtime enforcement. Complements the in-process contract below. |
| [`HLDSPEC_BROWNFIELD_CONTEXT_SAFETY_AND_GAP_LEDGER.md`](HLDSPEC_BROWNFIELD_CONTEXT_SAFETY_AND_GAP_LEDGER.md) | In-process context-safety validation contract: mandatory Gap Ledger, worker decomposition, compact receipts, evidence maps, RunSkeptic reconciliation, authority boundary. Backed by `hldspec/context_safety_gap_contracts.py`. Complemented by the doctrine doc above. |

---

## Active reference

| Doc | Purpose |
|---|---|
| [`HLDSPEC_ARTIFACT_CONTRACT_STYLE.md`](HLDSPEC_ARTIFACT_CONTRACT_STYLE.md) | Standard interface-contract shape for handoffs, prompts, reports, gap handoffs, and slice execution artifacts. |
| [`ENGINEERING_TOOLBOX.md`](ENGINEERING_TOOLBOX.md) | Durable engineering doctrine for constitution candidates, preferred choice selection, clean-software cards, and stage-safety guidance. |
| [`ANTI_DRIFT_CONTRACTS.md`](ANTI_DRIFT_CONTRACTS.md) | Non-droppable product, ownership, slice/mediator, and engineering-toolbox contracts that future changes must preserve. |
| [`ENGINEERING_QUALITY_GATES.md`](ENGINEERING_QUALITY_GATES.md) | Engineering practice gates (EQG-1..EQG-15) for implementation work **on the HLDspec repo**: TDD/red→green evidence, regression per bug fix, characterization before refactor, no test weakening, smallest slice, contract-first, fail-closed, single source of truth, ownership, read-only proof, evidence-based report. Repo-development governance — distinct from the target-software `ENGINEERING_TOOLBOX.md`. |
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
| [`JOURNEY3_CONTROLLER_TARGET_AGENT_BRIDGE.md`](JOURNEY3_CONTROLLER_TARGET_AGENT_BRIDGE.md) | Journey 3 controller/target/helper/agent-bridge terminology + UX operating model. Names the four roots (`hldspec_tool_root`, `controller_root`, `control_state_root`, `target_root`), the helper runtime capsule and adapter, and the proposed agent bridge (`.agents/hldspec/`, `bridge.json`, `SKILL.md`, `command_envelope`). Each term tagged EXISTS/PROPOSED; mode-dependent control-state rule; fail-closed safety. Design + terminology proposal — defers to `HLDSPEC_TERMINOLOGY_AND_FLOW.md` on conflict; bridge/symlink not yet implemented. |

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
