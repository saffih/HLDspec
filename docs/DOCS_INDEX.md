# HLDspec Docs Index

Authoritative reference vs active guidance vs archive/history. When in doubt, start here.

---

## Start here

| Doc | Purpose |
|---|---|
| [`../README.md`](../README.md) | Conceptual front door: what HLDspec does, the three journeys, and the normal workflow. |
| [`HLDSPEC_TERMINOLOGY_AND_FLOW.md`](HLDSPEC_TERMINOLOGY_AND_FLOW.md) | Authoritative canonical architecture, terminology, ownership boundaries, full flow, and SpecKit Run Card. Wins on conflicts. |
| [`../AGENTS.md`](../AGENTS.md) | Repo agent bootstrap and HLDspec invocation rules. |
| [`SPECKIT_SLICE_CONTROL.md`](SPECKIT_SLICE_CONTROL.md) | Technical slice-control model and generated slice artifact contract. |
| [`SPECKIT_PROXY_PROTOCOL.md`](SPECKIT_PROXY_PROTOCOL.md) | HLDspec-to-SpecKit handoff and proxy protocol. |
| [`SMOKE_SCENARIOS.md`](SMOKE_SCENARIOS.md) | Deterministic smoke scenarios, commands, target layout, and PASS/FAIL output contract. |
| [`REPO_LAYOUT.md`](REPO_LAYOUT.md) | Compact map of root files: active V2 source, shared parser, V1 pipeline, root docs, and the three test roots. |

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
| [`USER_RUN_MODEL.md`](USER_RUN_MODEL.md) | Simple user workflow: start, status, review, continue, speckit, diff, doctor. |
| [`AGENT_FIRST_PRODUCT_MODEL.md`](AGENT_FIRST_PRODUCT_MODEL.md) | Agent-first product model: users start sessions; scripts are tools. |
| [`RUNSKEPTIC_EVIDENCE_QUALITY.md`](RUNSKEPTIC_EVIDENCE_QUALITY.md) | RunSkeptic evidence field contract. |
| [`CONTEXT_TAILORING_PROTOCOL.md`](CONTEXT_TAILORING_PROTOCOL.md) | Context tailoring for subagents. |
| [`AGENT_ARTIFACT_HYGIENE.md`](AGENT_ARTIFACT_HYGIENE.md) | Policy for ad hoc docs, archive records, scratch output, target artifacts, and cleanup metadata. |

---

## Runtime entrypoints

| Script / Module | Role |
|---|---|
| `scripts/hldspec_agent_session.py` | Agent-first facade: start/status/review/continue/diff/doctor/speckit-doctor/operator-state (alias speckit-state). |
| `scripts/hldspec_smoke_slice_e2e.py` | Production smoke scenario for source package, mirror, anchors, slice artifacts, and optional tmux visibility. |
| `scripts/hldspec_v2.py` | V2 CLI entry point. |
| `scripts/hldspec_run.sh` | Canonical run entry for the full pipeline. |
| `scripts/project_first_run.sh` | First-time workspace setup. |
| `scripts/project_continue.sh` | Resume / status check. |
| `scripts/first_run_readonly.sh` | Bootstrap read-only analysis. |
| `hldspec/machines/project.py` | Orchestrator machine. |
| `hldspec/skeptic_schema.py` | RunSkeptic canonical finding schema. |

---

## Archive / historical

Historical docs are point-in-time RunSkeptic reviews and superseded design docs. They are not active references unless a current doc points to them explicitly.

Full archive contents: [`docs/archive/`](archive/)
