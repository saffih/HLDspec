# HLDspec — Task Tracker

Living task list. Update this when work starts, completes, or new gaps are found.

---

## Done (2026-05-25)

| Task | What | Files |
|---|---|---|
| Gate fix | `plan_quality.decision` green condition was `"FIX"` (never produced for clean plan); corrected to `"PASS"` | `hldspec/machines/spec_build_plan.py`, `scripts/render_hldspec_checkpoint.py`, `scripts/build_target_spec_work_order.py` |
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
| REFACTOR_PROGRAM.md | Updated with status, gaps, correct model routing | `docs/REFACTOR_PROGRAM.md` |
| CLAUDE.md | Project reference for new sessions | `CLAUDE.md` |
| TASKS.md (this file) | Living task tracker | `TASKS.md` |

---

## P0 — COMPLETE ✓

All P0 items done. HLDspec is now end-to-end complete (pipeline gates through to SpecKit execution).

---

## P1 — Important gaps, do soon

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
