# HLDspec — Task Tracker

Living task list. Update this when work starts, completes, or new gaps are found.

---

## Done (2026-05-25)

| Task | What | Files |
|---|---|---|
| Gate fix | `plan_quality.decision` green was `"FIX"`; corrected to `"PASS"` | `hldspec/machines/spec_build_plan.py` |
| Negative-path tests | 13 gate tests covering all green/non-green conditions | `tests_v2/test_spec_build_plan_quality_gate.py` |
| Workspace path guard | Fail fast if file path passed where directory expected | `hldspec/machines/project.py` |
| Handoff doc decoupling | `write_handoff_docs()` moved out of gate machine into orchestrator | `hldspec/machines/speckit_prework.py`, `hldspec/machines/project.py` |
| Reply parser | Deterministic UX: `next/ok/accept all/option` → checkpoint decision | `hldspec/reply_parser.py`, `tests_v2/test_reply_parser.py` |
| Constitution guard | Detect when regeneration silently wipes CONTRACT-*/DATA-* rules | `hldspec/prework_contracts.py`, `tests_v2/test_constitution_augmentation_guard.py` |
| Stale fixture sweep | Fixed all test fixtures using broken `FIX+KEEP_PLAN` combination | 5 test files |
| Artifact completeness validators | `missing_pm_pack_keys`, `missing_architect_pack_keys`, `shallow_dossier_fields` | `hldspec/prework_contracts.py`, `tests_v2/test_artifact_completeness_gates.py` |
| Stale prework detection | `stale_prework_artifacts()` checks mtime of prework vs plan | `hldspec/prework_contracts.py`, `tests_v2/test_stale_prework_detection.py` |
| SpecKitExecutionMachine (P0) | Post-approval execution driver: constitution → features in dependency order | `hldspec/machines/speckit_execution.py`, `hldspec/machines/project.py` |
| SpecKitExecutionMachine tests | 20 tests: missing inputs, constitution phase, all feature phases, completion | `tests_v2/test_speckit_execution_machine.py` |
| SKEPTIC-CONTRACT-001 | Canonical RunSkeptic schema: `SkepticFinding`, `FIELD_ALIASES`, normalization helpers | `hldspec/skeptic_schema.py` |
| SKEPTIC-CONTRACT-002 | Producer emits all required evidence fields; `unknowns` default `"none"` | `hldspec/skeptic_schema.py` |
| SKEPTIC-TEST-001 | 21 contract tests: schema parity, missing/empty fields, integration | `tests/test_skeptic_contract.py` |
| SKEPTIC-ORCH-001 | Evidence-quality REWORK_REQUIRED blocks ready gate; exact artifact in message | `scripts/hldspec_ready_gate.py`, `tests/test_skeptic_orch.py` |
| DOC-SOT-001 | Authoritative docs index; alignment script updated; pre-existing failure fixed | `docs/DOCS_INDEX.md`, `scripts/run_hldspec_alignment_review.py` |
| PROCESS-001 | Preflight checks: merge, staged, unstaged, untracked, divergence | `scripts/preflight_check.py`, `tests/test_preflight_check.py` |
| P1 — Parallel PM + Architect extraction | Both pack builders now run concurrently in `first_run_readonly.sh` | `scripts/first_run_readonly.sh` |
| P1 — Testing quality gate | `specs_missing_test_plans()`: UT + UI/UX required; technical specs exempt from UI/UX | `hldspec/prework_contracts.py`, `tests_v2/test_testing_quality_gate.py` |
| P2 — Canonical entry point | `hldspec_run.sh` now runs preflight before delegating | `scripts/hldspec_run.sh` |
| P2 — Observability | `build_hldspec_state.py`: stale artifact warnings + concise audit header in rendered output | `scripts/build_hldspec_state.py` |
| P2 — Legacy test cleanup | Removed 4 legacy tests with V2 replacements | `tests_legacy/` |
| P2 — Docs archive | 8 superseded docs moved to `docs/archive/` | `docs/archive/` |
| REFACTOR_PROGRAM.md | Updated with status, gaps, correct model routing | `docs/REFACTOR_PROGRAM.md` |
| CLAUDE.md | Project reference for new sessions | `CLAUDE.md` |
| TASKS.md (this file) | Living task tracker | `TASKS.md` |

---

## P0 — COMPLETE ✓

All P0 items done. HLDspec is end-to-end complete.

---

## P1 — COMPLETE ✓

All P1 items done.

---

## P2 — COMPLETE ✓

All P2 items done.

### Residual (no urgency)

- **Legacy tests**: 39 remain in `tests_legacy/`. 27 fail due to stale fixtures or API changes. Each needs a same-commit V2 replacement before removal.
- **Docs archive**: 3 docs (`FIRST_RUN.md`, `CONTEXT_BUDGET.md`, `TARGET_SPEC_CONTEXT.md`) have active references — deferred until references are updated.
- **Orchestration state**: `HLDSPEC_AGENT_COMMAND.md` and `HLDSPEC_ORCHESTRATION_CONTRACT.md` referenced by legacy tests — deferred.

---

## Live SpecKit invocation (2026-05-26)

**HLDspec can now actually drive SpecKit instead of only gating on human JSON.**
This closes the core "it runs but produces no implementation" failure.

| Item | Status | Files |
|---|---|---|
| `SpecKitInvoker` — headless `claude /speckit-<skill>` per phase | ✅ Done | `hldspec/speckit_invoker.py` |
| Full SpecKit toolchain phases | ✅ Done | order: SPECIFY→CLARIFY→PLAN→CHECKLIST→TASKS→ANALYZE→IMPLEMENT |
| Per-phase model routing (cost discipline) | ✅ Done | constitution/analyze=opus, specify/clarify/plan/implement=sonnet, checklist/tasks=haiku |
| Injectable invoker into `SpecKitExecutionMachine` (None=gated default) | ✅ Done | `hldspec/machines/speckit_execution.py` |
| **Anti-hollow-completion gate**: advance only if artifacts produced, not exit code | ✅ Done | `InvocationResult.verified`; git-signature change detection |
| State-version guard: live mode discards stale/simulated state | ✅ Done | `STATE_VERSION=2` |
| Tests (invoker, artifact gate, live mode, stale-state) | ✅ Done | `tests_v2/test_speckit_invoker.py`, `test_speckit_execution_machine.py` |

### Resolved decisions
- **Design ownership / auto-implement boundary**: resolved by the three-journey product model in `docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md` §13. Implementation Guidance is guidance and reassessment, not default auto-implementation. The live `SpecKitInvoker` auto-drive-all-phases path remains an opt-in capability only; default operation is mediator/user-steered with bounded prompts, slice scope, stop conditions, and explicit approvals.
- **Slice-control ownership**: settled by the source-package model. HLDspec generates `implementation_slices.json`, `implementation_slicing_policy.md`, and `slice_test_policy.md` once in `.hldspec/source_package/` and mirrors them read-only into `.specify/source/`. `AGENTS.md` and `templates/orchestrator/AGENTS.md` point implementing agents to those files. HLDspec provides and bounds; the user or Agent Mediator enforces during runtime. `SpecKitExecutionMachine` operating at feature granularity is by design.

### Open decisions (need human call)
- **`/home/sio/flow` vs `~/code/flow/impl`**: a Flow substrate was hand-built reading the HLD. Decide whether it's the implementation target the pipeline writes into, or discarded.

### Still TODO (from RunSkeptic + user)
- **Default output = numbered spec list respecting existing project numbering.** Prior code has `existing_specs_scan`/`highest_number` (`tests/test_hldspec_speckit_ready.py`); wire it into the live/queue path so new specs continue an existing project's numbering.
- **Gap analysis (desired vs. actual)** — NEW capability: when the HLD changes or a feature is added, derive specs THEN diff against the current implementation to surface the delta (what to add/change) and guide the feature work, before writing code. Needed for existing/evolving projects, not just greenfield.
- ~~Verify the real mechanism~~ — **Done (2026-07-11):** one real headless `claude --print` invocation through the default `SpecKitInvoker` (TASKS phase, `claude --model haiku` alias accepted) proved live against a disposable non-Flow target. Distinct from the earlier `docs/FIRST_LIVE_E2E_PROOF.md` (Opus/IMPLEMENT fixture). Record: `docs/SPECKIT_INVOKER_TASKS_HAIKU_LIVE_PROOF.md` (PR #154). This is one TASKS-phase invocation, not the first-ever live invocation and not a multi-phase proof.
- **Prove minimal chain before relying on all 8 phases** — still open; the 2026-07-11 proof covers one phase only.
- **`SpecKit drive` live proof**: `hldspec/speckit_drive_loop.py` + `scripts/speckit_drive_loop.py` (non-stop multi-bundle loop, opt-in trigger documented in `docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md` §"User trigger vocabulary") are built and unit-tested with an injected runner. Running it live still depends on proving a real bundle run — still open; not established by the 2026-07-11 single-phase proof.
- **Durable SpecKit invocation audit log** — contract ratified 2026-07-11: `docs/SPECKIT_INVOCATION_AUDIT_LOG_CONTRACT.md` (see `docs/HLDSPEC_DEVELOPMENT_BACKLOG.md` P1-019). Roadmap is Slices A-E in the contract. Slice A (path/schema) done: `hldspec/speckit_invocation_audit.py` — canonical pointer-aware path helper, closed schema-version-1 STARTED/FINISHED validator, deterministic NDJSON line serialization. No writer, no append/lock/fsync, no `SpecKitInvoker`/drive-loop wiring, no reader, no diagnostics — Slices B-E remain not started.

---

## Architecture anchor (2026-05-25)

**Stability architecture document added.** `docs/HLDSPEC_STABILITY_ARCHITECTURE.md` anchors the five principles (state machine core, artifact contracts, ports/adapters, event log, validator plugins) to known failure modes. Runtime implementation of message bus, port interfaces, and event log is **intentionally deferred** — the document names the direction; implementation happens in small slices when a specific failure mode becomes acute.

Next small slices (no urgency order):
1. Artifact contract registry skeleton (`hldspec/artifact_contracts.py`)
2. Artifact freshness validator (extend `stale_prework_artifacts()`)
3. Typed prework approval artifact with schema_version
4. tests_v2 discovery in ready gate
5. Shell-vs-ProjectMachine parity test
6. Replace last deprecated "target-spec generation" markers in active docs

---

## Production-readiness (2026-05-26)

| Item | Status | Files |
|---|---|---|
| Single gate semantics | ✅ Done | hldspec/gates.py |
| Fix plan-green bug (FIX/HANDLED accepted as green) | ✅ Done | scripts/build_hldspec_state.py |
| Gate used in SpecBuildPlanMachine | ✅ Done | hldspec/machines/spec_build_plan.py |
| Prework gate + artifact freshness in SpeckitPreworkMachine | ✅ Done | hldspec/machines/speckit_prework.py |
| Gate alignment: render_hldspec_checkpoint.py | ✅ Done | scripts/render_hldspec_checkpoint.py |
| Shell-vs-machine parity tests | ✅ Done | tests_v2/test_shell_vs_machine_parity.py |
| Event log wired into ProjectMachine | ✅ Done | hldspec/machines/project.py |
| HumanDecisionPort stub | ✅ Done | hldspec/ports.py |
| Option packet skeleton | ✅ Done | hldspec/option_packet.py |

---

## Architecture decisions record

| Decision | Rationale |
|---|---|
| Gate machines only gate | Prevents partial-state risk on retry; single responsibility |
| Graph and queue from same `ordered_features` | Enforces no-divergence at generation time |
| `plan_quality.decision == "PASS"` for green | "FIX" = has findings; "PASS" = clean. Fixed 2026-05-25. |
| PM + Architect extraction parallel | Independent reads from same source; merge at Answer Dossier |
| Reply parser separate from renderer | Parser is pure logic; renderer is presentation; different change rates |
| Constitution augmentation additive | `build_speckit_constitution_from_contracts.py` skips covered rule_ids; safe to re-run |
| RunSkeptic schema in `hldspec/` | Both producer and reviewer import from single source of truth |
| Preflight before hldspec_run | Prevents multi-agent runs on dirty/diverged state |
| `unknowns` default `"none"` | Makes evidence quality gate return PASS for auto-generated findings |

## Development handoff protocol

| Item | Status | Files |
|---|---|---|
| HLDspec repo-development handoff | Added protocol and generator for handing repo work between models/agents/sessions | `docs/HLDSPEC_DEVELOPMENT_HANDOFF.md`, `scripts/hldspec_dev_handoff.py`, `tests_v2/test_dev_handoff.py` |

## Development handoff and backlog

| Item | Status | Files |
|---|---|---|
| HLDspec repo-development handoff protocol | Added canonical protocol and generator | `docs/HLDSPEC_DEVELOPMENT_HANDOFF.md`, `scripts/hldspec_dev_handoff.py` |
| HLDspec repo-development backlog | Added durable backlog for unfinished design and implementation work | `docs/HLDSPEC_DEVELOPMENT_BACKLOG.md` |
| Agent bootstrap pointer | `AGENTS.md` first screen points every agent to the handoff and backlog docs | `AGENTS.md` |

## Journey 3 — `hldspec refresh-target` (2026-06-13)

| Item | Status | Files |
|---|---|---|
| Target-write capability with file-by-file safety classification (7 classes, dry-run default, `--apply` to write) | ✅ Done | `hldspec/refresh_target.py`, `scripts/hldspec_refresh_target.py` |
| Manages `next_feature_AGENTS.md` (always regenerable) and `.specify/memory/constitution.md` (managed marker block; unmanaged constitution gets a review plan, never overwritten) | ✅ Done | `hldspec/refresh_target.py` |
| 12 focused tests: dry-run, create/update helper, constitution create/refresh/review, unowned files, spec progress artifacts, dirty tree, product files, skipped/conflict reporting, status-pointer wording | ✅ Done | `tests_v2/test_refresh_target.py` |
| Docs: refresh-target as Journey 3's only target-write capability, kept separate from the read-only status/run-card driver | ✅ Done | `docs/SPECKIT_DRIVING_MODELS.md`, `docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md` |

## Toolchain Driver Boundary + helper selection (2026-06-18)

Smallest usable slice making HLDspec's existing SpecKit-driving capability
helper-explicit: surfaces which toolchain/helper is selected vs recommended,
and gives the boundary between HLDspec-owned and tool-owned files a name and a
mutation-safety test, instead of leaving it as prose only.

| Item | Status | Files |
|---|---|---|
| Ownership-zone classifier (`HLDSPEC_OWNED`/`ADAPTER_MIRROR`/`READ_ONLY_EVIDENCE`/`TOOL_OWNED_FORBIDDEN`/`AMBIGUOUS_ESCALATE`, default-deny on unknown paths) | ✅ Done | `hldspec/toolchain_driver_boundary.py` |
| Selected-helper state: `.hldspec/helper_selection.json` writer/reader, validated against `helper_registry.operational_helpers()`; composite toolchain status (recommended vs selected vs effective helper, recommendation staleness via `registry_sha256`) | ✅ Done | `hldspec/helper_selection.py` |
| `status` command: new `## Toolchain` section (toolchain, recommended/selected/effective helper, staleness notes); new `select-helper` command (`--helper-id` or `--use-recommended`) | ✅ Done | `scripts/hldspec_agent_session.py` |
| Tests: zone classification, write/read/validation of helper selection, composite status, CLI wiring, and a mutation-safety test proving `status`/`select-helper` never write under `.specify/` or `specs/` | ✅ Done (30 tests) | `tests_v2/test_toolchain_driver_boundary.py`, `tests_v2/test_helper_selection.py`, `tests_v2/test_toolchain_driver_status_cli.py` |
| Docs: Toolchain Driver Boundary contract (vocabulary bridge, zones, SpecKit driver path, ISG Governance future-seam, SourceBinding bridge table) | ✅ Done | `docs/TOOLCHAIN_DRIVER_BOUNDARY.md`, registered in `docs/DOCS_INDEX.md`; updates to `docs/JOURNEY3_HELPER_CONTRACT.md` §13, `docs/HLDSPEC_DEVELOPMENT_BACKLOG.md` P1-012, `README.md`, `docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md` command list |

**Deliberately deferred (not in this slice):** live `EXECUTE_WITH_APPROVAL`
drive-loop proof (still unproven per the "Live SpecKit invocation" section
above), `NextActionPacket`/READY gating, inquiry/gap ledger implementation
(docs-only, separately gated per `docs/JOURNEY2_INQUIRY_LEDGER_CONTRACT.md`),
ISG Governance implementation (seam documented only), and refactoring
`refresh_target.py` to import the new boundary module (left as-is; surgical
change discipline — two call sites agreeing on the same boundary is sufficient,
they do not need to share code).

**Residual / pre-existing doc drift noticed, not fixed (out of scope):**
`docs/JOURNEY3_HELPER_CONTRACT.md` lines 15 and 121/124 still say
`helper_recommendations` is "not emitted by any code", which predates the
2026-06-16 `build_helper_recommendations` slice and is now stale; §13 already
has a correct "now emitted" note. Pre-existing inconsistency, unrelated to this
slice.
