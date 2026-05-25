# HLDspec — Task Tracker

Living task list. Update this when work starts, completes, or new gaps are found.

---

## Done (this session — 2026-05-25)

| Task | What | Files |
|---|---|---|
| Gate fix | `plan_quality.decision` green condition was `"FIX"` (never produced for clean plan); corrected to `"PASS"` | `hldspec/machines/spec_build_plan.py`, `scripts/render_hldspec_checkpoint.py`, `scripts/build_target_spec_work_order.py` |
| Negative-path tests | 13 gate tests covering all green/non-green conditions | `tests_v2/test_spec_build_plan_quality_gate.py` |
| Workspace path guard | Fail fast if file path passed where directory expected | `hldspec/machines/project.py` |
| Handoff doc decoupling | `write_handoff_docs()` moved out of gate machine into orchestrator | `hldspec/machines/speckit_prework.py`, `hldspec/machines/project.py` |
| Reply parser | Deterministic UX: `next/ok/accept all/option` → checkpoint decision | `hldspec/reply_parser.py`, `tests_v2/test_reply_parser.py` |
| Constitution guard | Detect when regeneration silently wipes CONTRACT-*/DATA-* rules | `hldspec/prework_contracts.py`, `tests_v2/test_constitution_augmentation_guard.py` |
| Stale fixture sweep | Fixed all test fixtures using broken `FIX+KEEP_PLAN` combination | 5 test files |
| REFACTOR_PROGRAM.md | Updated with status, gaps, correct model routing | `docs/REFACTOR_PROGRAM.md` |
| CLAUDE.md | Project reference for new sessions | `CLAUDE.md` |
| TASKS.md (this file) | Living task tracker | `TASKS.md` |

---

## P0 — Must do before HLDspec is end-to-end complete

### Post-approval SpecKit execution machine

**What:** Build `hldspec/machines/speckit_execution.py` — the machine that drives SpecKit after approval.

**Why missing:** `ProjectMachine` ends at `ApprovalGateMachine`. After approval, the system has no machine enforcing:
- Constitution runs before first spec
- Features are invoked in dependency order
- Each feature follows: clarify → plan → tasks
- Next feature only starts after current one completes
- Implementation is blocked until tasks are approved

**Design:**

```
SpecKitExecutionMachine
  reads: speckit_invocation_queue.json
  tracks: active_feature_index, active_phase (CONSTITUTION/CLARIFY/PLAN/TASKS/DONE)
  
  states:
    CONSTITUTION_PENDING      → human checkpoint: approve constitution
    FEATURE_PENDING           → invoke SpecKit for next feature
    SPECKIT_CLARIFY_ACTIVE    → checkpoint: clarify complete?
    SPECKIT_PLAN_ACTIVE       → checkpoint: plan approved?
    SPECKIT_TASKS_ACTIVE      → checkpoint: tasks approved?
    FEATURE_COMPLETE          → advance to next feature
    ALL_FEATURES_COMPLETE     → done
  
  gates:
    - SpecKit not invoked until constitution approved
    - Each phase requires human approval before next
    - Implementation blocked until tasks approved
    - No spec skipped in dependency order
```

**State persistence:** `speckit_execution_state.json` in sync dir — tracks which feature and phase is active across runs.

**Model:** `CRITICAL` for design review, `STRONG` for implementation.

---

## P1 — Important gaps, do soon

### Artifact completeness gates (systemic)

**What:** Machines check artifact *existence* but not *completeness*. Machines that gate on PM, Architect, or Dossier artifacts should validate required fields before proceeding.

**Root cause:** Single systemic pattern — add `missing_required_keys()` validators for critical artifacts and call them at machine read-time.

**Artifacts that need completeness checks:**
- `speckit_product_manager_pack.json` — must contain: users, jobs_to_be_done, user_journeys, use_cases, user_stories, acceptance_criteria
- `speckit_architect_pack.json` — must contain: constitution_rules, component_boundaries, interface_contracts, dependency_order, technical_risks
- Answer Dossier — must contain: named_capabilities, interface_contracts, data_ownership, integration_paths, dependency_reasons, acceptance_criteria

**Where to add:** `hldspec/prework_contracts.py` (new functions) + called from `SpeckitPreworkMachine` at read time.

**Model:** `STRONG`

---

### Stale prework detection

**What:** If `spec_build_plan.json` is updated after prework was built, the prework package may be stale. No check exists.

**Fix:** Add `generated_at` timestamp to critical artifacts. At machine read time, check that prework package is newer than spec_build_plan.

**Artifacts to timestamp:** `speckit_prework_package.md`, `constitution_update_plan.json`, `speckit_invocation_queue.json`.

**Model:** `ROUTINE`

---

### Parallel PM + Architect extraction as explicit machine states

**What:** PM and Architect extraction currently happen sequentially inside `first_run_readonly.sh`. They are independent reads from the same source and should run in parallel.

**Why:** Faster, clearer role boundaries, enables correct model routing (PM extraction = ROUTINE, Architect extraction = STRONG).

**Design:** Two separate script invocations in `first_run_readonly.sh` run concurrently. Or: two new machines `PmExtractionMachine` and `ArchitectExtractionMachine` that run in parallel from `ProjectMachine`, each with a completeness gate.

**Model:** `STRONG` for design, `ROUTINE` for extraction scripts.

---

### Testing quality gate (UT + UI/UX)

**What:** HLDspec must enforce that every spec includes:
- UT coverage plan (which behaviours need unit tests)
- UI/UX test plan (which user journeys need end-to-end tests)

Exception: specs marked `no_direct_user_story: true` (technical foundations) are exempt from UI/UX test requirements but not from UT.

**Where to add:** As a quality flag in spec build plan enrichment + a check in prework quality review.

**Model:** `STRONG`

---

## P2 — Clean up, consolidate, improve

### Canonical rebuild entry point

**What:** Multiple shell entry points (`first_run_readonly.sh`, `hldspec_prework.sh`, `project_continue.sh`, `hldspec_run.sh`, etc.) with no enforced order. Easy to run one script out of sequence and produce inconsistent state.

**Fix:** One canonical `hldspec_run.sh` that enforces order and prevents ad-hoc partial runs. Others become internal helpers or are deprecated.

**Model:** `ROUTINE`

---

### Observability / audit summary

**What:** After a run or restart, no concise view of: current checkpoint, what's blocking, last regeneration chain, what's safe to do next.

**Fix:** Extend `build_hldspec_state.py` — one concise machine-readable + human-readable status output.

**Model:** `ROUTINE`

---

### Legacy test cleanup

**What:** 43 tests in `tests_legacy/`. Some cover behavior already covered by `tests_v2/`; some cover deprecated flows.

**Policy:** Only delete a legacy test when a stronger V2 test covers the same behavior in the same commit.

**Model:** `ROUTINE`

---

### Docs archive

**What:** `docs/` contains 57 files, many are point-in-time RunSkeptic reviews from earlier sessions (HLDSPEC_RUNSKEPTIC_*.md). These are not living docs — they are historical records.

**Fix:** Move all `HLDSPEC_RUNSKEPTIC_*.md` and superseded TODO files to `docs/archive/`. Keep living references in `docs/`.

**Status:** Partially done this session (see below). Remaining cleanup TBD.

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
