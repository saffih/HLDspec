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
