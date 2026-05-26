# HLDspec — Project Reference

Read this first when starting a new session on this repo.

---

## What HLDspec is

HLDspec turns a source HLD into a dependency-aware SpecKit execution path.

It is a **workflow engine**, not a code generator. It prepares the context, extracts the architecture and product requirements, validates quality, and hands off to SpecKit in the right order. It never implements application code itself.

```
Source HLD (read-only)
    │
    ├──→ PM extraction        (parallel)
    │    users, journeys, stories, AC, scope
    │                                         ──→ Answer Dossier
    └──→ Architect extraction (parallel)
         contracts, boundaries, SoT,                  │
         dependencies, tech risks                     │
              │                                       │
              └──→ Constitution                       │
                                                      ▼
                                          Spec build plan
                                          (enriched with PM + Arch context)
                                                      │
                                          Spec build plan gate
                                          (human: accept / fix / redesign)
                                                      │
                                          SpecKit prework package
                                          (quality review, dossier, queue, graph)
                                                      │
                                          Prework approval gate
                                          (human: approve / rework)
                                                      │
                                          SpecKit execution (P0 — not yet built)
                                          constitution → features in dependency order
                                          each feature: clarify → plan → tasks
                                                      │
                                          Implementation (only after approved tasks)
```

---

## Architecture

### Core module: `hldspec/`

| File | Role |
|---|---|
| `state_machine.py` | Canonical types: MachineStatus, CheckpointKind, MachineResult, Checkpoint, HumanQuestion, ArtifactRef |
| `result_renderer.py` | Renders MachineResult and Checkpoint to human-readable text |
| `reply_parser.py` | Maps user replies (next/ok/accept all/option) to checkpoint decisions |
| `prework_contracts.py` | Shared validation rules: constitution keys, arch disposition blockers, augmentation guards |
| `handoff_docs.py` | Builds architecture_handoff.md and product_handoff.md from sync artifacts |
| `script_io.py` | Shared IO helpers for scripts (load_json, write_json, sync_dir) |
| `command_runner.py` | Subprocess runner used by machines |

### Machines: `hldspec/machines/`

Machines are the control flow layer. They gate, not generate.

| Machine | What it does |
|---|---|
| `project.py` — `ProjectMachine` | Orchestrator. Runs the full chain in order. |
| `raw_hld_conversion.py` — `RawHldConversionMachine` | Checks HLD conversion decisions. Blocks if TBD. |
| `apply_hld_conversion.py` — `ApplyHldConversionMachine` | Applies answered conversion decisions to workspace HLD. |
| `spec_build_plan.py` — `SpecBuildPlanMachine` | Gates on spec build plan quality. Green = PASS + KEEP_PLAN + no conflicts + continue_true. |
| `speckit_prework.py` — `SpeckitPreworkMachine` | Gates on prework quality review. Blocks on REWORK_REQUIRED or BLOCKER findings. |
| `approval_gate.py` — `ApprovalGateMachine` | Final human approval before SpecKit. |

**Pipeline chain:**
```
ProjectMachine
  → RawHldConversionMachine
  → ApplyHldConversionMachine
  → SpecBuildPlanMachine
  → SpeckitPreworkMachine
  → write_handoff_docs()        ← orchestration, not a machine
  → ApprovalGateMachine
  → [SpecKitExecutionMachine]   ← P0: not yet built
```

### Scripts: `scripts/`

71 scripts. They handle generation — extracting, building, reviewing artifacts. Machines read the artifacts scripts produce. Scripts do not control flow.

Key scripts:
- `first_run_readonly.sh` — bootstraps workspace, runs all read-only analysis
- `project_first_run.sh` — first-time workspace setup
- `project_continue.sh` — resume/status check
- `apply_spec_build_plan_decisions.py` — sets plan_quality.decision (PASS/FIX/CONFLICT/DECOMPOSE)
- `build_speckit_prework_plan.py` — builds invocation queue + dependency graph from same ordered_features
- `build_speckit_constitution_from_contracts.py` — augments constitution with CONTRACT-*/DATA-* rules
- `enrich_spec_build_plan_with_answer_context.py` — joins PM + Arch context by source_hld_sections
- `hldspec_v2.py` — CLI entry point

### Tests

| Directory | What |
|---|---|
| `tests_v2/` | Active — machine contracts, behavior, negative paths. Run these. |
| `tests/` | Active — script-level integration tests. |
| `tests_legacy/` | Reference only. Do not delete without replacing with V2 tests. |

Run: `python3 -m unittest discover -s tests_v2 -v`

---

## Key invariants

**Never violate these:**

1. Source HLD is read-only. Workspace copy only.
2. SpecKit is not invoked until `SPECKIT_PREWORK_APPROVAL_GATE` is passed and prework is APPROVED.
3. Final SpecKit specs are not written manually by HLDspec.
4. Application code is not implemented by HLDspec.
5. Gate machines only gate — no generation inside gate machines.
6. `plan_quality.decision == "PASS"` is the green state for a clean plan. "FIX" means has-findings. "CONFLICT"/"DECOMPOSE" are blocking.
7. The graph (`feature_dependency_graph.json`) and queue (`speckit_invocation_queue.json`) are generated from the same `ordered_features` list and must never diverge.
8. Constitution augmentation (CONTRACT-*/DATA-* rules) must survive regeneration.

---

## Model routing

Use abstract model tiers in artifacts and prompts. Map them to concrete models
at runtime so Codex, Claude, and Devin runs preserve the same workflow rules.

| Tier | Use for | Codex | Claude | Devin |
|---|---|---|---|---|
| `MODEL_ROUTINE` | Deterministic extraction, summaries, inventories, evidence lookup | `gpt-5.5 low` | `Haiku 4.5` | `SWE 1.6` |
| `MODEL_DEFAULT` | Orchestration, repo inspection, focused implementation | `gpt-5.5 medium` | `Sonnet 4.6` | `SWE 1.6` under credit pressure; `codex 4.3 code` when available |
| `MODEL_STRONG` | Bounded module work, single-slice refactors, adapters, tests for new seams | `gpt-5.5 high` | `Sonnet 4.6` | `Sonnet 4.5` |
| `MODEL_CRITICAL` | Architecture decisions, contract changes, role boundaries, RunSkeptic verdicts, promotion gates | `gpt-5.5 xhigh` | `Opus 4.7` | `Opus 4.6` |

Rule: weakest sufficient model creates; strongest necessary model promotes.

`SWE 1.6` may draft, edit, run tests, and perform mechanical review, but it must
not approve architecture, constitution, source-of-truth, API, data ownership,
dependency, security, rollout, split/merge, or promotion decisions.

---

## UX contract

User-facing interaction must be simple:

```
CHECKPOINT  <kind>
  <blocking reason>
  <what's flagged, if any>

  → next        continue / accept current state
  → accept all  bulk-accept all flagged items with default rationale
  → fix         trigger fix/rebuild
  → <option>    explicit decision (e.g. ACCEPT_WITH_RATIONALE)

> _
```

- `next` / `ok` / `continue` → `CONTINUE` when no open questions
- `accept all` → maps to first ACCEPT/APPROVE option on each open question
- Exact option name → routed directly
- User never inspects internal JSON files unless a decision is specifically blocked on them

Reply parser: `hldspec/reply_parser.py`

---

## Quality gates

HLDspec blocks or warns when:

| Condition | Gate |
|---|---|
| Planned spec lacks context and is not a technical foundation | Spec build plan gate |
| `plan_quality.decision` is CONFLICT or DECOMPOSE | Spec build plan gate |
| Graph order and invocation queue diverge | Prework quality review |
| Constitution required keys missing | `prework_contracts.missing_constitution_keys()` |
| Architecture disposition unresolved | `prework_contracts.architecture_disposition_blockers()` |
| Constitution augmentation wiped | `prework_contracts.constitution_augmentation_blockers()` |
| Prework status is REWORK_REQUIRED or has BLOCKER findings | SpeckitPreworkMachine |
| SpecKit invoked before approval | Every checkpoint forbidden_actions |

---

## Working on this repo

**Before any change:**
1. Read `TASKS.md` for current pending work
2. Run `python3 -m unittest discover -s tests_v2 -v` — must be green
3. Check `git status` and `git log --oneline -5`

**Making changes:**
- Surgical edits only — no speculative cleanup of adjacent code
- Match existing style
- Tests first for any behavioral change
- Commit message format: `fix/feat/refactor/test/docs(scope): description`

**RunSkeptic:**
- Apply for: architecture changes, contract changes, promotion decisions, gate changes
- Source: `/Users/saffi/code/skeptic/skeptic.md`
- Never use memory or summaries as substitute for the actual file

**Testing convention:**
- New machine behavior → test in `tests_v2/`
- Script-level behavior → test in `tests/`
- Legacy tests: only delete with a same-commit V2 replacement

---

## Docs map

| File | Purpose |
|---|---|
| `CLAUDE.md` (this file) | Session bootstrap — read first |
| `TASKS.md` | Living task list — P0/P1/P2 pending work |
| `AGENTS.md` | Agent bootstrap for HLDspec workflow invocation |
| `docs/REFACTOR_PROGRAM.md` | Refactor program — completed/in-progress/outstanding |
| `docs/ARCHITECTURE_V2.md` | V2 architecture details |
| `docs/CANONICAL_FLOW.md` | Canonical flow reference |
| `docs/HLDSPEC_V2_AGENT_ROLES.md` | Role definitions for subagents |
| `docs/TEST_STRATEGY_V2.md` | Test strategy |
| `docs/archive/TODO_V2.md` | Historical — superseded by TASKS.md |
| `docs/archive/` | Point-in-time RunSkeptic reviews and old design docs |
