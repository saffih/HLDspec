# HLDspec Docs Index

Authoritative reference vs archive/history. When in doubt, use this page.

---

## Active / Authoritative

These docs are living references. Follow links in CLAUDE.md for session bootstrap.

| Doc | Purpose |
|---|---|
| [`../CLAUDE.md`](../CLAUDE.md) | Session bootstrap — read first every session |
| [`../TASKS.md`](../TASKS.md) | Living task list — P0/P1/P2 pending work |
| [`../AGENTS.md`](../AGENTS.md) | Agent bootstrap for HLDspec workflow invocation |
| [`ARCHITECTURE_V2.md`](ARCHITECTURE_V2.md) | V2 architecture: machines, contracts, pipeline |
| [`CANONICAL_FLOW.md`](CANONICAL_FLOW.md) | Canonical pipeline flow reference |
| [`HLDSPEC_V2_AGENT_ROLES.md`](HLDSPEC_V2_AGENT_ROLES.md) | Subagent role definitions |
| [`REFACTOR_PROGRAM.md`](REFACTOR_PROGRAM.md) | Refactor program: completed / in-progress / outstanding |
| [`TEST_STRATEGY_V2.md`](TEST_STRATEGY_V2.md) | Test strategy and conventions |
| [`SPECKIT_PROXY_PROTOCOL.md`](SPECKIT_PROXY_PROTOCOL.md) | HLDspec ↔ SpecKit handoff protocol |
| [`JUDGE_LED_REVIEW_PROTOCOL.md`](JUDGE_LED_REVIEW_PROTOCOL.md) | Judge-led human review protocol |
| [`RUNSKEPTIC_EVIDENCE_QUALITY.md`](RUNSKEPTIC_EVIDENCE_QUALITY.md) | RunSkeptic evidence field contract |
| [`CONSTITUTION_RULE_QUALITY.md`](CONSTITUTION_RULE_QUALITY.md) | Constitution rule quality gate |
| [`CONTEXT_TAILORING_PROTOCOL.md`](CONTEXT_TAILORING_PROTOCOL.md) | Context tailoring for subagents |
| [`HLDSPEC_V2_HANDOFF_DOCS.md`](HLDSPEC_V2_HANDOFF_DOCS.md) | Handoff doc specification |
| [`HLDSPEC_STABILITY_ARCHITECTURE.md`](HLDSPEC_STABILITY_ARCHITECTURE.md) | Stability architecture principles: artifact contracts, ports/adapters, event log, validator plugins |
| [`BACKEND_TECHNOLOGY_RECOMMENDATION.md`](BACKEND_TECHNOLOGY_RECOMMENDATION.md) | Short approved backend toolbox with defaults, upgrades, and triggers |
| [`HLDSPEC_RUNTIME_DOCUMENT_USAGE.md`](HLDSPEC_RUNTIME_DOCUMENT_USAGE.md) | Runtime rules for using guidance docs correctly during HLDspec runs |
| [`SOFTWARE_DESIGN_PRINCIPLES.md`](SOFTWARE_DESIGN_PRINCIPLES.md) | Reusable software design principles for HLD generation, constitution extraction, spec packages, prompts, RunSkeptic, and cost/context economy |
| [`HLD_TO_TARGET_WORKSPACE.md`](HLD_TO_TARGET_WORKSPACE.md) | Target workspace model: `target/`, `targetHLD/`, HLD groups, spec packages, dependency order |
| [`CONSTITUTION_GENERATION.md`](CONSTITUTION_GENERATION.md) | Principle-level target constitution generation rules |
| [`SPECKIT_DELEGATION_PROMPTS.md`](SPECKIT_DELEGATION_PROMPTS.md) | Generated prompts for SpecKit phase delegation |
| [`MEDIATOR_PROMPT_PROTOCOL.md`](MEDIATOR_PROMPT_PROTOCOL.md) | Mediator prompt protocol for Devin/Claude/Codex target agents |

### Runtime entrypoints

| Script / Module | Role |
|---|---|
| `scripts/hldspec_v2.py` | CLI entry point |
| `scripts/hldspec_run.sh` | Canonical run entry (full pipeline) |
| `scripts/project_first_run.sh` | First-time workspace setup |
| `scripts/project_continue.sh` | Resume / status check |
| `scripts/first_run_readonly.sh` | Bootstrap read-only analysis |
| `hldspec/machines/project.py` | Orchestrator machine |
| `hldspec/skeptic_schema.py` | RunSkeptic canonical finding schema |

---

## Archive / Historical

These docs are **historical records only** — point-in-time RunSkeptic reviews and
superseded design docs. They are not updated and should not be used as active references.

| Doc | What it was |
|---|---|
| `docs/archive/HLDSPEC_RUNSKEPTIC_*.md` | Point-in-time RunSkeptic cycle reviews |
| `docs/archive/HLDSPEC_IMPLEMENTATION_TODO.md` | Historical TODO — superseded by TASKS.md |
| `docs/archive/HLDSPEC_V2_APPLY_DEBUG.md` | Debug session notes |
| `docs/archive/CHUNKED_AGENT_PROTOCOL.md` | Deprecated agent protocol |
| `docs/archive/EXTERNAL_AGENT_PROMPT.md` | Deprecated agent prompt |
| `docs/archive/ARCHITECTURE_ENHANCEMENT_OPTIONS.md` | Enhancement options planning doc — superseded by `HLDSPEC_STABILITY_ARCHITECTURE.md` |
| `docs/archive/CONTEXT_BUDGET.md` | Context budget protocol for agent/model bounded reads |
| `docs/archive/FIRST_RUN.md` | First-run read-only cycle walkthrough |
| `docs/archive/TARGET_SPEC_CONTEXT.md` | Target spec context rules — HLD evidence → spec package |

Full archive contents: [`docs/archive/`](archive/)

---

## How to find things fast

- **What stage am I at?** → `TASKS.md`
- **What does the pipeline do?** → `CANONICAL_FLOW.md`
- **What does a machine do?** → `ARCHITECTURE_V2.md` + `hldspec/machines/`
- **RunSkeptic schema?** → `hldspec/skeptic_schema.py` + `RUNSKEPTIC_EVIDENCE_QUALITY.md`
- **SpecKit handoff?** → `SPECKIT_PROXY_PROTOCOL.md`
- **How to run tests?** → `TEST_STRATEGY_V2.md`

| [`AGENT_FIRST_PRODUCT_MODEL.md`](AGENT_FIRST_PRODUCT_MODEL.md) | Agent-first product model: users start sessions; scripts are tools |
| [`USER_RUN_MODEL.md`](USER_RUN_MODEL.md) | Simple user workflow: start, status, review, continue, speckit, diff, doctor |
| [`HLDSPEC_PRODUCT_SCORECARD.md`](HLDSPEC_PRODUCT_SCORECARD.md) | Product scorecard for simplicity, target workspace, RunSkeptic, and agent-first execution |

| [`HLDSPEC_DEVELOPMENT_HANDOFF.md`](HLDSPEC_DEVELOPMENT_HANDOFF.md) | Development handoff protocol for handing the HLDspec repo between models/agents/sessions |

| [`HLDSPEC_DEVELOPMENT_HANDOFF.md`](HLDSPEC_DEVELOPMENT_HANDOFF.md) | Canonical development handoff protocol for handing HLDspec repo work between models/agents/sessions |
| [`HLDSPEC_DEVELOPMENT_BACKLOG.md`](HLDSPEC_DEVELOPMENT_BACKLOG.md) | Durable backlog for unfinished HLDspec repo-development work and open design decisions |
