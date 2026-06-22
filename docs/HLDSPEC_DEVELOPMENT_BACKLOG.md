# HLDspec Development Backlog

## Purpose

This is the durable backlog for developing HLDspec itself.

It captures unfinished work and open design decisions that must survive handoff between models, agents, and sessions.

Use together with:

- `docs/HLDSPEC_DEVELOPMENT_HANDOFF.md`
- `.hldspec-dev/handoff/HANDOFF.md`
- `TASKS.md`
- `docs/HLDSPEC_PRODUCT_SCORECARD.md`
- `docs/HLDSPEC_PRINCIPLE_ENFORCEMENT_MATRIX.md`

## Core product direction

HLDspec is agent-first and stateless.

Rules:

1. HLDspec core keeps no hidden internal memory.
2. Reads and writes are external.
3. Before source and target are known, the agent interviews the user to understand intent.
4. Once source and target are known, durable run state is written externally under the target workspace.
5. HLDspec development handoff state is written externally under `.hldspec-dev/`.
6. Scripts are deterministic tools for agents.
7. Product usage is agent-first.
8. Direct script use is allowed for maintainer/debug usage only.

## Current readiness mark - 2026-05-26

This mark reflects the current `main` branch after the command-surface, path-contract, interview-artifact, context-economy, validator, promotion-gate, UX-output, self-dogfood, and promoted-capability RunSkeptic evidence patches.

Scale:

```text
0 = absent
5 = partially designed and partially implemented
10 = product-ready with enforcement and tests
```

| Area | Mark | Current assessment |
|---|---:|---|
| Development handoff discipline | 7 | Canonical handoff/backlog docs and generator exist; generated handoff still needs stronger open-action, conflict, and RunSkeptic status quality. |
| Agent-first product model | 6 | Public facade is narrowed to `start`, `status`, `review`, `continue`, `diff`, `doctor`, and `speckit-doctor`; richer commands are marked future or legacy/debug; full end-to-end orchestration coverage remains open. |
| Target workspace clarity | 7 | New-layout paths are stabilized: `target/.hldspec/sync/`, `target/.hldspec/events.jsonl`, `target/targetHLD/HLD.md`, `target/targetHLD/raw/HLD.raw.md`, and SpecKit-owned `target/.specify/`; broader migration coverage remains. |
| TargetWorkspaceAdapter | 7 | Adapter supports legacy/new modes and `hldspec continue` uses ProjectMachine with new-layout metadata; remaining machines still need migration coverage. |
| Use-case/API definition | 6 | Use-case catalog and command matrix exist; implementation and journey tests do not yet cover every use case. |
| Stateless external IO | 7 | `start --state-location external` externalizes `.hldspec/` and `prompts/` into a run store; `targetHLD/` stays in target as a product artifact; `.hldspec-run.json` (pointer) is written and gitignored. All facade read sites resolve via pointer. External mode is single-machine only — not supported for cross-machine handoff. |
| Context economy | 6 | Context packs, allowed evidence, forbidden reads, bounded SpecKit prompts, and context validators exist; guarded product-flow integration remains. |
| SpecKit delegation prompts | 6 | Seven bounded SpecKit phase prompts are generated per package; package discovery/invocation wiring and deeper semantic validators remain. |
| Validators and regression gates | 6 | Context prompt validator, promotion gate, command/path tests, self-dogfood smoke, and matrix tests exist; domain validators remain open. |
| RunSkeptic enforcement | 6 | Prompt validators and promotion gate enforce RunSkeptic trigger/status requirements, including promoted capability RunSkeptic PASS evidence; gate-machine and handoff propagation remain open. |
| Promotion gate | 6 | Promotion gate blocks validator ACTION/CONFLICT, missing context validation, unresolved checkpoints, readiness marks above evidence, and promoted capabilities without RunSkeptic PASS evidence; not yet wired into a complete product promotion command. |
| UX/output quality | 6 | `status`, `review`, and `doctor` show decision-oriented output with blockers, validation status, promotion status, next safe action, and final summary; `start`, `diff`, and stage-aware checks need more coverage. |
| Self-dogfood | 6 | HLDspec can run a smoke flow on HLDspec backlog evidence without invoking SpecKit; full self-hosted SpecKit delegation remains out of scope and unproven. |

Overall current mark: 6/10.

Reason: the foundational contracts and several enforcement gates now exist, but HLDspec is not yet product-ready. Remaining blockers are guarded product-flow integration, end-to-end journey coverage, stale-artifact/diff handling, domain validators, and RunSkeptic status propagation through handoff/gate-machine outputs.

## Current Journey Status — 2026-06-23

Snapshot after merging PR #38 (`ef3f934`). "Done" here means: the **currently
implemented** Journeys 1/2/3 are verified against `main`; it does **not** mean every
proposed future feature is implemented. Full suites green on `ef3f934`: `tests_v2`
1391 OK, `tests` 173 OK.

| Journey | Status | Evidence | Deferred / future |
|---|---|---|---|
| **J1 — HLD Shaping / SDD-ready gate** | PASS_WITH_DEFERRED_WORK | `hldspec/hld_readiness.py`, `docs/JOURNEY1_SDD_READY_GATE.md`; tests `test_hld_verify_coverage`, `test_raw_hld_conversion_machine`, `test_hld_marking`, `test_constitution_from_hld_verify` (30 focused OK) | P1-012: missing-whole-section detection; `accepted_risks` capture wiring |
| **J2 — SpecKit Groundwork / source + architecture package** | PASS_WITH_DEFERRED_WORK | `hldspec/hld_source_package.py`, `hldspec/journey2_architecture_package.py`; tests `test_source_package`, `test_journey2_architecture_package` (65 focused OK) | `architecture_package.json` 13 reasoning fields stay human-owned (emitted ACTION-by-default; PR #26 analysis); P1-013 inquiry/gap ledger + lens registry |
| **J3 — Build Loop Supervision / Agent Handoff Pack** | PASS_WITH_DEFERRED_WORK | pointer-aware control plane + Agent Handoff Pack (`hldspec/agent_handoff_pack.py`, PR #38); tests `test_journey3_*`, `test_agent_handoff_pack`, `test_agent_first_cli_contract`, `test_hldspec_smoke_slice_e2e` (104 focused OK) | bridge / `command_envelope` (P1-016, PROPOSED only); P1-018 compat cleanup; post-#37 read-only dogfood not yet run (P1-016/K) |

All three journeys are safe for current use in their implemented scope. No journey is
"perfect" or feature-complete; the deferred column is the honest remainder.

PR status at snapshot: #35/#36/#37/#38 merged; #29 closed/superseded; #26 open draft
(UPDATE_NEEDED — substantively current DO_NOT_PATCH analysis, but base SHA `507b398`
predates #30–#38 and one sentence describes `architecture_package.json` emission as
target-local only without the post-#35 `control_state_root` resolution).

## Current implementation notes

### Context economy

Implemented:

- `hldspec/context_economy.py`
- `scripts/build_speckit_context_prompts.py`
- `target/.hldspec/context_packs/`
- `target/.hldspec/allowed_evidence.json`
- `target/.hldspec/forbidden_reads.md`
- bounded per-package prompts under `target/prompts/speckit/<package-id>/`

Current status: mostly addressed as artifact generation and validation. Residual work is product-flow wiring and semantic validation beyond required markers.

### SpecKit prompts

Implemented:

```text
target/prompts/speckit/<package-id>/
  01-specify.md
  02-clarify.md
  03-plan.md
  04-research-data-contracts.md
  05-tasks.md
  06-implement.md
  07-verify-runskeptic.md
```

Current status: mostly addressed for bounded prompt generation. Residual work is package discovery, invocation queue integration, and validation of produced SpecKit outputs.

### Validators

Implemented:

- `hldspec/validators.py`
- `scripts/validate_hldspec_target.py`
- `target/.hldspec/validation/context_prompt_validation.json`
- `target/.hldspec/validation/context_prompt_validation.md`

Validated now:

- `allowed_evidence.json`
- `forbidden_reads.md`
- context pack JSON
- required prompt context markers
- RunSkeptic triggers
- valid model tiers
- forbidden broad-read phrases
- implement-phase human approval guards
- generated source-package `engineering_guidelines.md` exists and validates
  before SpecKit prework approval

Still open:

- backend upgrade trigger validation
- selected-principle phase/implementation evidence validation
- constitution purity validation
- package unit/integration/e2e testability validation
- dependency graph and invocation queue parity
- generated handoff pointer validation

### Engineering Toolbox stewardship

Implemented:

- `maintainability.capability_stewardship` is an always-selected Engineering
  Toolbox baseline card.
- Generated `engineering_guidelines.md` now passes the maintenance method to
  target projects: key capability changes must update durable docs, tests,
  contracts/runbooks when relevant, agent guidance, and anti-drift coverage for
  protected behavior.
- Repo and generated orchestrator `AGENTS.md` include the matching new
  capability maintenance rule for HLDspec/project agents.

Still open:

- phase/report validators do not yet block missing per-capability stewardship
  evidence beyond the generated guidance and pinned docs/tests.

### RunSkeptic enforcement

Implemented:

- generated SpecKit prompts include RunSkeptic trigger points
- context prompt validation blocks prompts that omit RunSkeptic triggers
- promotion gate blocks validator ACTION/CONFLICT findings
- promotion gate blocks promoted capabilities unless RunSkeptic status is PASS with evidence
- `MachineResult` carries structured RunSkeptic status and evidence metadata
- `SpeckitPreworkMachine` blocks explicit RunSkeptic ACTION/CONFLICT before SpecKit continuation

Still open:

- remaining gate-machine outputs must surface RunSkeptic PASS/ACTION/CONFLICT directly
- generated handoff packets must include structured RunSkeptic evidence, not only a status string
- review output must link RunSkeptic findings to exact evidence and next safe action
- missing evidence must be enforced beyond prompt text and promotion-scorecard cases

### Promotion gate

Implemented:

- `hldspec/promotion.py`
- `scripts/check_hldspec_promotion_gate.py`
- `target/.hldspec/validation/promotion_gate.json`
- `target/.hldspec/validation/promotion_gate.md`

Blocks now:

- validator ACTION/CONFLICT findings
- missing context validation when prompts exist
- unresolved human checkpoints
- missing implementation approval guards
- readiness marks above 7 without evidence
- promoted capabilities without RunSkeptic PASS evidence

Still open:

- guarded product promotion command/path
- richer scorecard fields and generated promotion summaries
- product-flow wiring so promotion checks run automatically at the right junctions

### UX output

Implemented:

- `docs/HLDSPEC_OUTPUT_CONTRACT.md`
- `docs/HLDSPEC_QUALITY_REQUIREMENTS.md`
- decision-oriented `status`, `review`, and `doctor` output

Required output sections now include:

- blockers
- validation status
- promotion status
- next safe action
- final summary

Still open:

- same output discipline for `start` and `diff`
- stage-aware `doctor` checks
- CLI journey tests for every supported command path

### Self-dogfood

Implemented:

- `docs/HLDSPEC_SELF_DOGFOOD_CONTRACT.md`
- `docs/HLDSPEC_PRINCIPLE_ENFORCEMENT_MATRIX.md`
- `tests_v2/test_self_dogfood_flow.py`

The smoke flow runs against HLDspec repository evidence, writes target session/interview/context/validation/promotion artifacts, and does not invoke SpecKit.

Still open:

- full self-hosted SpecKit handoff
- repeated stale-input and changed-guidance rebuild tests
- evidence capture for red-to-green RunSkeptic cycles

### Promoted capability RunSkeptic evidence

Implemented:

- `tests_v2/test_promoted_capability_runskeptic_gate.py`
- promotion gate requirement that every promoted capability must include RunSkeptic PASS evidence
- blocking behavior for missing, ACTION, or CONFLICT RunSkeptic status

Still open:

- generated promoted-capability scorecard creation
- human-readable promotion diff linking each promoted capability to exact evidence

## P0 backlog - still blocks product-stable claims

### P0-001 External IO enforcement across all write paths

Status: partially addressed; still P0.

Covered now:

- `start` preserves source HLD content.
- `start` writes durable target-product artifacts under `target/`.
- self-dogfood smoke verifies source evidence remains unchanged.
- target state paths are explicit and tested for key flows.

Still needed:

- tests proving every write path writes only to approved target or `.hldspec-dev/` locations
- enforcement for non-start flows, generated prework artifacts, SpecKit delegation prompts, and promotion reports
- explicit failure when a product flow attempts durable writes outside the path contract

### P0-002 Guarded product-flow integration

Status: open P0.

Problem: context economy, validators, RunSkeptic checks, and promotion gate exist as tools/gates, but the product flow still needs stronger automatic sequencing.

Acceptance:

- `hldspec continue` knows when to build context prompts, validate them, run promotion checks, and stop.
- `status`, `review`, and `doctor` agree on current blockers and next safe action.
- no product path can proceed from generated prompts to implementation while validation or promotion is ACTION/CONFLICT.

### P0-003 End-to-end journey tests

Status: open P0.

Required journeys:

- start from raw HLD source
- resume existing target
- review checkpoint and capture human decision
- continue after approval
- stop on unresolved conflict
- generate context packs and bounded prompts
- validate generated prompts
- run promotion gate
- inspect status/review/doctor output

Acceptance:

- tests use the public facade where possible
- tests prove direct low-level scripts are not required for product usage
- failures show next safe action rather than only stack traces

### P0-004 Stale artifact and diff handling

Status: open P0.

Required artifacts:

```text
target/.hldspec/input_manifest.json
target/.hldspec/artifact_hashes.json
```

Required detection:

- source changed
- guidance changed
- generated prompts stale
- SpecKit outputs changed
- dependency graph changed
- invocation queue stale

Acceptance:

- `hldspec diff` reports stale or changed artifacts clearly
- `hldspec doctor` reports whether the target is safe to continue
- `hldspec speckit-doctor` reports target-level SpecKit readiness
- regeneration scope is bounded to affected outputs

### P0-005 Domain validators before product-stable promotion

Status: open P0.

Required validators:

- backend upgrade has trigger
- selected principle has evidence
- constitution contains no feature-specific content
- each package has unit/integration/e2e testability
- dependency graph and invocation queue match
- generated handoff points to canonical backlog and handoff protocol

Acceptance:

- validators write machine-readable and human-readable reports
- ACTION/CONFLICT findings block promotion
- tests cover failing and passing cases

### P0-006 RunSkeptic status propagation

Status: open P0.

Covered now:

- prompt validators check RunSkeptic triggers
- promotion gate checks promoted capability RunSkeptic PASS evidence
- `MachineResult` carries structured RunSkeptic status and evidence metadata
- `SpeckitPreworkMachine` blocks explicit RunSkeptic ACTION/CONFLICT before SpecKit continuation

Still needed:

- remaining gate machines surface RunSkeptic PASS/ACTION/CONFLICT status directly
- generated handoff packet lists structured RunSkeptic evidence, not only a status string
- review output links RunSkeptic findings to exact evidence and next safe action

## Mostly addressed former P0 items

These remain important but no longer represent the top stale-truth gaps.

| Former item | Current status | Residual location |
|---|---|---|
| User interview capability | Mostly addressed for `start --source --target --comment`; future interactive discovery remains deferred. | P1-003 |
| TargetWorkspaceAdapter | Mostly addressed for new-layout ProjectMachine entry; migration coverage remains. | P1-004 |
| Event and state ownership | Mostly addressed for canonical new paths; full write-path enforcement remains. | P0-001 |
| Agent-first CLI facade integration | Mostly addressed for current public command surface and `continue`; full journey coverage remains. | P0-003 |
| Context economy enforcement | Mostly addressed as generated artifacts plus validator; product-flow integration remains. | P0-002 |
| SpecKit delegation prompts | Mostly addressed as seven generated bounded phase prompts; package/invocation wiring remains. | P1-005 |
| Context and prompt validators | Mostly addressed for prompt/context guardrails; domain validators remain. | P0-005 |
| README/AGENTS alignment | Mostly addressed for command-surface direction; final docs sweep remains. | P1-006 |
| Promotion scorecard gate | Mostly addressed as an internal target gate; product promotion command/path remains. | P0-002 |
| Self-dogfood smoke | Mostly addressed for smoke without SpecKit; full self-hosted delegation remains future. | P1-007 |

## P1 backlog

### P1-001 Backend toolbox cleanup

Refine `docs/BACKEND_TECHNOLOGY_RECOMMENDATION.md`.

Known issue:

```text
Domain structure | Clean architecture | Ports/adapters
```

This mixes architecture style and implementation boundary pattern.

Better split:

```text
Domain structure:
Default = modular clean layers
Upgrade = explicit boundary layer

Boundary isolation:
Default = direct internal interface
Upgrade = port/adapter
Trigger = external dependency, replaceability, test seam, agent/tool boundary
```

### P1-002 Development handoff generator maturity

Generated `.hldspec-dev/handoff/HANDOFF.md` should include:

- pointer to canonical handoff protocol
- pointer to backlog
- git state
- changed files
- tests run
- tests required
- RunSkeptic status
- open actions
- open conflicts
- next safe step
- do-not-do list

### P1-003 Interactive interview discovery

The current implemented path writes interview artifacts when source and target are provided.

Future work:

- no-source interview for intent and source discovery
- source-only flow for target selection
- resume/adopt interview for existing targets
- structured clarification capture before writing

### P1-004 Complete machine migration through TargetWorkspaceAdapter

Residual work:

- migrate remaining machines away from hardcoded legacy paths
- keep legacy/debug compatibility explicit
- add tests that fail if a new path model is introduced without adapter and docs updates

### P1-005 Package discovery and SpecKit invocation wiring

Residual work:

- connect bounded prompts to final package/dependency/invocation artifacts
- validate package prompts against the dependency graph
- ensure each generated prompt names allowed evidence, forbidden reads, model tier, stop condition, and expected outputs

### P1-006 Documentation alignment sweep

Residual work:

- README leads with agent-first product usage
- AGENTS, CLAUDE, USER_RUN_MODEL, and use-case docs agree on current/future/legacy commands
- direct scripts are documented as agent/maintainer tools, not the product workflow

### P1-007 Expanded self-dogfood

Residual work:

- self-run with changed HLDspec guidance
- stale-input rebuild detection
- generated promoted-capability scorecard
- RunSkeptic red-to-green evidence capture

### P1-008 HLD build terminology

Choose one product term and use it consistently.

Candidate:

```text
hldspec start
```

Meaning:

```text
start an agent-guided HLDspec session
```

Optional future command:

```text
hldspec build-hld
```

Meaning:

```text
build or improve target/targetHLD/HLD.md from sources and interview answers
```

Avoid using `build` ambiguously for both HLD preparation and product implementation.

### P1-009 Tiered re-sync: iterate on the HLD without wiping the workspace

Problem (recurring real scenario, 2026-06-11):

```text
The HLD was wrong. The user edits the source HLD and re-runs.
The freshness gate is binary (whole-file sha256), so any edit makes the whole
workspace "stale" and the only offered remedies are full wipe
(HLDSPEC_FRESH=1) or rm -rf. The wipe destroys answered decision queues,
plan decisions, and approvals — the most expensive artifacts in the workspace —
and disconnects the run from already-generated specs.
For an early iterating project this punishes the normal loop, not the
exception.
```

Root cause: artifacts with very different replacement costs share one
lifecycle. Tier them:

```text
Tier 0 — human answers (decision queues, approvals).
         Never auto-deleted. Carried forward and revalidated.
Tier 1 — extracted packs and plans (PM pack, architect pack, spec build plan).
         Model-time cost. Regenerate only for dirty sections/features.
Tier 2 — rendered derivations (bundle prompts, handoff docs, queue md).
         Deterministic and cheap. Safe to regenerate every time
         (the existing `regenerate prompts` action is the model).
```

Status 2026-06-11: slices A, C, and E implemented (`hldspec/hld_sync.py`,
`scripts/hldspec_sync.py`, `tests_v2/test_hld_sync.py`, trigger `HLDspec sync`
in the canonical doc). B and D remain open.

Implementation slices, cost-ordered (build A+C+E first; B+D only after A
proves deltas are usually small):

- A. Section fingerprints (small): extend `source_freshness.json` with a
  per-section sha256 (conversion already chunks the HLD into sections).
  On change, report `changed_sections: [...]` instead of binary stale.
- B. Dirty-feature mapping (small-medium): join changed sections against the
  `source_hld_sections` already recorded per feature in the spec build plan
  to get the dirty feature set; untouched features keep their status.
- C. Done ledger (small): `speckit_execution_state.assess_spec` already
  verifies spec.md/plan.md/tasks.md per spec. Record the section-hash
  snapshot when a spec completes, yielding per-feature status
  `DONE | DONE_STALE | PENDING`. Evidence-based done-checking, consistent
  with the anti-hollow-completion gate.
- D. Decision carry-forward (medium): on re-run, revalidate each answered
  decision — section unchanged: carry forward silently; section changed:
  re-open only that question. Mark superseded answers; never delete them.
- E. `HLDspec sync` trigger (small once A+C exist): one cheap idempotent
  action, safe to run every time. Refresh fingerprints -> report changed
  sections, dirty features, and the DONE/DONE_STALE/PENDING table ->
  regenerate Tier-2 artifacts -> propose the minimal next action.
  Never deletes anything. `HLDSPEC_FRESH=1` remains the explicit
  nuclear option only.

Out of scope here: diffing against hand-written external code (full
brownfield gap analysis, TASKS.md "Gap analysis (desired vs. actual)").
This entry covers the cheaper, more frequent case: HLDspec's own previous
outputs plus an edited HLD.

### P1-010 Unify "done" evidence semantics across the two assessors

Reproduced seam (2026-06-12): for the same spec with `spec.md` and no
validation evidence —

```text
discovery phase ledger (target_discovery.py)   : UNVERIFIED, safety ACTION
execution assessment (speckit_execution_state) : specify DONE, resume -> plan
```

The preparation plane (status/doctor/continue/operator-state) blocks on
missing passing evidence; the execution plane (drive loop, resume
instructions, "skip phases already marked DONE") trusts artifact presence.
A hollow artifact from a crashed run is skipped past validation by the
execution plane while the control plane blocks. Mitigations today: the
prework approval gate before any drive, the per-phase RunSkeptic gates in
bundle prompts, and the drive loop's no-progress stop.

Decision needed: one DONE vocabulary. Either execution assessment consults
the same passing-evidence rule (strict, may stall resumes on legacy
artifacts), or it stays presence-based but `next_action` must instruct
re-validation of presence-only phases instead of skipping them.

Related smaller items:

- `hld_sync` resolves its sync dir via `select_execution_sync_dir` and does
  not follow `.hldspec-run.json` controller pointers; fine for legacy
  workspaces, wrong if pointed at an external-mode target.
- `speckit_drive_loop.prework_approved` checks target-local dirs only; on an
  external-mode target it misses controller approval and blocks (fail-safe,
  but should resolve the pointer once drive supports external mode).

### P1-011 Bind the source package to its target — RESOLVED 2026-06-12

A wholesale-copied `.hldspec/` tree with a valid manifest plus anchor map is
still trusted lineage (agent_session is target-bound since 2026-06-12, the
source package is not). Record the target path and source hash inside
`source_package.json` at build time and verify both at discovery. Natural
precondition for managed greenfield evolution.

Resolved by Slice 1 of `docs/reviews/runskeptic_landscape_20260612-114242_UTC.md`:
`source_package.json` now carries `created_by`/`created_at`/`binding_schema_version`/
`target_path`/`target_path_sha256`/`source_ref`/`source_sha256`, and
`target_discovery` classifies the binding as `BOUND_MATCH` / `BOUND_MISMATCH` /
`UNBOUND_LEGACY` / `MISSING_BINDING` / `INVALID_BINDING`. Only `BOUND_MATCH`
packages count as trusted lineage; mismatched or invalid bindings distrust the
target fail-closed (even over a valid agent session); legacy/unbound packages
warn and are never fully trusted. Source-hash mismatch is checked against the
`.hldspec-run.json` pointer when both hashes exist. Tests:
`tests_v2/test_target_discovery.py::SourcePackageBindingTests`,
`tests_v2/test_source_package.py` binding round-trip cases.

### P1-012 Deferred journey-contract runtime gaps

Surfaced by the Journey 1/2/3 contract work (2026-06-16). Docs-only in the
contracts; implementation deferred. Do not act on these until explicitly gated.

**Journey 1:**

- **Missing-section detection.** The verdict heuristic catches unsourced claims,
  TBD/high-risk-without-verify, and declared `CONFLICTS_WITH`, but cannot detect a
  *missing whole required section* (e.g. no architecture section at all). Absence
  is not currently counted as `unresolved`, so the check is incomplete. Add a
  required-section presence check in `hld_readiness.py` so absence → BLOCKED.
- **`accepted_risks` wiring.** `build_hld_readiness_check` emits `accepted_risks: []`
  today. The acceptance-capture step (human agrees to a provisional item and it is
  recorded) is contracted in `docs/JOURNEY1_SDD_READY_GATE.md` but not wired.
  Journey 2 may promote on `HLD_READY_WITH_ACTIONS` only after this capture exists.

**Journey 2:**

- **Emit `helper_recommendations`.** ✓ DONE (2026-06-16).
  `hldspec/hld_source_package.py::build_helper_recommendations` emits
  `helper_recommendations.json` during `build_source_package_content`. File is in
  `AUTHORITATIVE_FILES` (manifest-hashed), excluded from `MIRROR_FILES` and
  `REQUIRED_FILES`. Tests in `tests_v2/test_source_package.py::HelperRecommendationsTests`.

### P1-013 Journey 2 inquiry/gap ledger + lens registry (docs/JOURNEY2_INQUIRY_LEDGER_CONTRACT.md, added 2026-06-17)

Contract is docs-only. Implementation slices (do not start without a separate gated
prompt):

- **Slice A — `lens_registry.py`:** 4 builtin lenses (DOMAIN, ARCHITECTURE,
  QUALITY, TOOL_HELPER), `validate_lens`, `validate_lens_registry`, `lens_json()`.
  Mirrors the pattern of `helper_registry.py`. No wiring into compilation path yet.
- **Slice B — `inquiry_ledger.json` + `gap_register.json` in source package:**
  Add both to `AUTHORITATIVE_FILES` + `_MIRROR_EXCLUDED` where required. Not in
  `REQUIRED_FILES` (migration safety). Add gate conditions to
  `SOURCE_PACKAGE_APPROVAL_GATE`: ESCALATED unresolved → BLOCKED; BLOCKER gap open
  → BLOCKED; WARNING gap → ACTION.
- **Slice C — Compilation wiring:** Wire lens registry into `build_source_package_content`
  so that the four builtin lenses generate question candidates from the HLD anchors
  and slice set, producing a draft `inquiry_ledger.json` and `gap_register.json`.
  Question resolution (ASSUMED / ANSWERED_FROM_HLD / ESCALATED) happens at this
  step or via human input before promotion.
- **Slice D — Advisory views:** Render `open_questions.md` and
  `answered_assumptions.md` from the ledger. Render `test_strategy.md` from
  QUALITY-lens output. All three in `AUTHORITATIVE_FILES` + `_MIRROR_EXCLUDED`,
  not in `REQUIRED_FILES`.

Tests added with each slice in `tests_v2/`. See §13 of the contract for the full
14-test list. Do not implement until Slice A is separately reviewed and gated.

**Journey 3:**

- **Store/read selected `helper_id` at runtime.** ✓ DONE (2026-06-18).
  `hldspec/helper_selection.py` writes/reads `.hldspec/helper_selection.json`
  (validated against `helper_registry.operational_helpers()`), surfaced via
  `scripts/hldspec_agent_session.py status` (`## Toolchain` section) and the new
  `select-helper` command. See `docs/TOOLCHAIN_DRIVER_BOUNDARY.md`. Tests:
  `tests_v2/test_helper_selection.py`, `tests_v2/test_toolchain_driver_boundary.py`,
  `tests_v2/test_toolchain_driver_status_cli.py`.
- **Decide `EXECUTE_WITH_APPROVAL` contract placement.** The existing opt-in
  `SpecKitInvoker` / `SpecKit drive` loop is an `EXECUTE_WITH_APPROVAL` capability.
  Decide whether it belongs under `HelperContract` as a per-helper authority field,
  or remains a separate standalone capability. The contracts describe it as an
  opt-in exception but do not bind it formally to the `helper_id: speckit` entry.

**P1-012 addendum — Helper Bootstrap runtime (docs/HELPER_BOOTSTRAP_CONTRACT.md,
added 2026-06-16):**

The Bootstrap contract is docs-only. Implementation slices (do not start without
a separate gated prompt):

- Slice A: `registry.json` + `.hldspec/helpers/speckit/` entry for the existing
  `speckit` operational helper (retrofit, no behavior change).
- Slice B: Intake question runner → writes `INSPECTED_TOOL` JSON.
- Slice C: Capability probe checklist → writes `REVIEWED_HELPER` JSON or
  `REJECTED.json`.
- Slice D: `NextActionPacket` writer/renderer (formalize what
  `next_feature_readiness` already produces for speckit).
- Slice E: Human-approval gate for `APPROVED_HELPER` → `OPERATIONAL_HELPER`
  transition.

Do not implement until Slice A is separately reviewed and gated.

**Design note — storage separation (do not collapse these into one file):**

```text
source_package/helper_recommendations.json   = Journey 2 output: recommended/default
                                               helper set, rationale, per-helper fit.
.hldspec/helper_selection.json               = Journey 3 selected-helper state:
                                               which helper the human/agent chose
                                               and when. Written by Journey 3.
.hldspec/runtime/MANIFEST.json               = runtime provenance only: installed
                                               runtime version, source commit, vendor
                                               manifest. NOT the helper-selection SoT.
```

Reason: the runtime manifest describes the installed binary, not the product/helper
selection. Storing the selected helper in `MANIFEST.json` mixes runtime provenance
with product state and would create a hidden source-of-truth conflict between the
Journey 2 recommendation and the Journey 3 selection.

### P1-015 Engineering Quality Gates enforcement (docs/ENGINEERING_QUALITY_GATES.md, added 2026-06-21)

The policy is docs/governance only (`docs/ENGINEERING_QUALITY_GATES.md`): 15 gates
(EQG-1..EQG-15) for implementation work on the HLDspec repo — TDD/red→green evidence,
regression test per bug fix, characterization before refactor, no test weakening,
smallest slice, contract-first, compatibility/fail-closed, single source of truth,
explicit ownership, read-only proof, evidence-based report. Several gates are
currently **receipt-** or **judgment-**enforced only.

Follow-up (do not start without a separate gated prompt):

- Promote receipt-only gates to machine enforcement: add a `tests_v2/` check (e.g. a
  behavior-changing PR with no red→green evidence fails), and a corresponding row in
  `docs/HLDSPEC_PRINCIPLE_ENFORCEMENT_MATRIX.md` (whose own rule marks unenforced
  principles documentation-only / ACTION).
- Decide whether to promote the gates to a protected contract in
  `docs/ANTI_DRIFT_CONTRACTS.md` (would invoke that doc's change-policy).

Note: P1-014 (external target-artifacts placement contract) is reserved by the open
draft PR #29; this item is numbered P1-015 to avoid a merge collision.

### P1-016 Journey 3 controller/target/agent-bridge implementation (docs/JOURNEY3_CONTROLLER_TARGET_AGENT_BRIDGE.md, added 2026-06-21)

Terminology + UX are defined; the roadmap A–M below is named in the doc (§8) but
**not implemented**. None grant authority by themselves — approval gates stay
controller-owned. The doc's §8 is the authoritative roadmap; this is the tracking row.

- **A.** Canonical `.agents/hldspec/` bridge structure.
- **B.** `SKILL.md` + `bridge.json` (mirrors, never replaces, the `.hldspec-run.json`
  pointer).
- **C.** Optional provider shims (`.devin|.claude|.codex/hldspec/`) pointing at the
  canonical bridge.
- **D.** Bridge discovery from either `controller_root` or `target_root`.
- **E.** Bridge validation, fail closed: broken=BLOCKED, mismatch=BLOCKED, multiple
  candidates=BLOCKED, stale=ACTION/BLOCKED.
- **F.** Optional `Target Controller Link` symlink (`target/.agents/hldspec ->
  controller/.agents/hldspec`); untracked by default; broken/mismatched=BLOCKED.
- **G.** `helper_runtime_capsule` defined precisely per helper.
- **H.** Generic `HelperAdapter` + concrete `SpecKitAdapter` contract (formalizes
  `helper_selection.py` + Toolchain Driver).
- **I.** `command_envelope` typed schema (lift the session-packet shape in
  `hldspec/session_control.py`).
- **J.** Literal/path hardening that fails closed on accidental
  `target/.hldspec/source_package/` leaks in external mode (today only source-package
  split-brain is detected via `hld_source_package.source_package_split_brain`).
- **K.** Read-only dogfood against `~/code/flow` (no mutation, no helper/SpecKit run).
- **L.** Reassess **PR #29** (dogfood package-placement gap) after this contract lands.
- **M.** Reassess **PR #26** (Journey 2 architecture-package authoring) separately.

### P1-017 Reconcile canonical control-plane doc with external-controller mode (added 2026-06-21)

**Status: implemented by PR #37.**

`docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md` (canonical, test-locked by
`tests_v2/test_terminology_and_flow_docs.py`) now describes the control plane and
source package as resolved paths: default/no-pointer mode uses
`target_root/.hldspec/`, while the implemented Option-C external-controller mode
(PR #30/#32/#33/#34/#35) resolves the same control plane to
`controller_root/.hldspec/` when a `.hldspec-run.json` pointer is present. The
locked tests cover both modes and the target-local helper-runtime boundary.

### P1-018 Agent Handoff Pack pointer-aware path rendering (added 2026-06-22)

**Status: code path implemented; on-disk/schema rename deferred.**

The Journey 3 "mediator guidance" generator was renamed to the **Agent Handoff Pack**
and made pointer-aware (`hldspec/agent_handoff_pack.py`). Previously
`write_mediator_guidance_artifacts` built `TargetWorkspaceAdapter(...)` without a
`controller_root` and hard-coded `target/.hldspec/source_package/...` strings, so in
external-controller mode the packet, prompts, and rendered source-package paths leaked
into the target. They now resolve through `control_paths.resolve_controller_root` (the
same resolution Journey 3 uses): packet + prompts follow `control_state_root`
(controller in external mode), helper runtime (`.specify/source/`, `specs/`) stays
target-local. Locked by `tests_v2/test_agent_handoff_pack.py` (default + external mode,
terminology, compat shim) — the external-mode test fails if a target-local
`.hldspec/source_package/...` path reappears in generated handoff output.

Deferred (do not start without a separate gated prompt):

- **On-disk artifact rename:** `mediator/` → `agent_handoff/`, `mediator_packet.json`
  → `agent_handoff_packet.json`, `START_MEDIATOR.md`/`DEVIN_MEDIATOR_SKILL.md`/
  `CODEX_CLAUDE_MEDIATOR.md` → `AGENT_HANDOFF.md`/`DEVIN_AGENT_HANDOFF.md`/
  `DIRECT_AGENT_HANDOFF.md`. Kept legacy this slice to avoid breaking downstream
  consumers (`hldspec_agent_session.py` output, `scripts/hldspec_smoke_slice_e2e.py`,
  `tests_v2/fixtures/expected_smoke_artifacts.txt`, `cli_contract`).
- **Packet JSON key rename:** `mediator_boundaries` → `handoff_boundaries`,
  `speckit_paths` → `helper_runtime_paths`, etc. Kept legacy for schema stability.
- **Residual legacy sub-terms in rendered prose** kept for cross-locked tests
  (`Agent Mediator is not the Implementation Agent.`, the `Codex / Claude direct
  mediator mode` label). Reconcile with `docs/MEDIATOR_PROMPT_PROTOCOL.md`,
  `docs/ANTI_DRIFT_CONTRACTS.md`, and the canonical flow string in
  `docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md` (all test-locked) when those docs are renamed.
- **Remove the `hldspec/mediator_guidance.py` compatibility shim** once all consumers
  migrate to `hldspec/agent_handoff_pack.py`.

## P2 backlog

### P2-001 Optional workflow engine evaluation

Do not add a workflow engine now.

Trigger only if:

- persistent loop becomes too complex
- timers/retries/workers exceed simple state machine needs
- current adapter/machine model cannot safely express workflow

### P2-002 Microservices and event sourcing are not defaults

Keep these as rare optional tools.

Use only with RunSkeptic-approved triggers.

### P2-003 UI/accessibility templates

If HLDspec later generates UI-related package prompts, include accessibility checks:

- keyboard navigation
- screen reader labels
- contrast
- focus order
- semantic structure
- clear errors

## Open conflicts

### CONFLICT-001 Product workflow vs maintainer workflow

Decision:

```text
Product usage is agent-first.
Maintainer/debug usage may run scripts directly.
```

Required implementation:

- README leads with agent-first usage
- direct scripts are documented as tools/debug
- agents know scripts are not the public product workflow

### CONFLICT-002 Target layout migration strategy

Decision:

```text
Use TargetWorkspaceAdapter and migrate machines incrementally.
```

Implementation rule:

```text
Agent-first ProjectMachine calls use `layout="new"`.
Legacy/debug runs may keep `layout="legacy"` until migrated.
```

### CONFLICT-003 First-run and sync path ownership

Resolved decision:

```text
Should first-run review/sync artifacts live under target/.hldspec/, target/.specify/, or target/firstrun/.specify/sync/?
```

Decision:

- HLDspec-owned review and planning artifacts live under `target/.hldspec/sync/` for the agent-first layout.
- Event history lives under `target/.hldspec/events.jsonl`.
- SpecKit-owned final artifacts remain under `target/.specify/` and `target/specs/`.
- Legacy/debug runs may still read or write old `.specify/sync` shapes through the adapter during migration.

### CONFLICT-004 Use-case API doc vs current facade

Decision: keep the current public surface small; mark richer commands as future and old names as legacy/debug.

Current public commands: `start`, `status`, `review`, `continue`, `diff`, `doctor`, `speckit-doctor`, `operator-state`, `speckit-state`, `git-lifecycle`.

Future commands: `interview`, `prework`, `speckit`, `pause`.

Legacy/debug: `run`, `speckit-proxy`, direct low-level scripts.

### DOC-DRIFT-001 Command-surface drift (2026-05-29) — RESOLVED

The real public surface is `start`, `status`, `review`, `continue`, `diff`,
`doctor`, `speckit-doctor`, `operator-state` (alias `speckit-state`), and
read-only `git-lifecycle`, verified against `build_parser()` by
`tests_v2/test_product_readiness_docs.py`.

Resolved by the "align canonical command surface" commit:
`docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md` (HLDspec Product Facade) is now the single
canonical command-surface source. `README.md`, `docs/USER_RUN_MODEL.md`,
`docs/HLDSPEC_USE_CASES_AND_API.md`, `docs/DOCS_INDEX.md`, and `AGENTS.md` defer
to it and list all 10 commands. `USER_RUN_MODEL.md` and `HLDSPEC_USE_CASES_AND_API.md`
no longer self-declare a competing "canonical" surface. The README command-surface
test now binds to backtick-quoted command tokens; the use-case contract test now
asserts `operator-state`/`speckit-state` and read-only `git-lifecycle` as current.

- Remaining (deferred, not blocking): rename the root `Dev` session pointer to a
  self-describing name (e.g. `SESSION_RESTART.md`). Nothing in active code
  references the filename (only `docs/archive/`), so the rename is safe but is a
  user-preference call; it is documented in `docs/REPO_LAYOUT.md` for now.

## Gap: raw->anchored conversion exists but is not reachable from `agent_session --mode create`

Logged 2026-05-29 while anchoring the Baton Flow HLD (`~/code/flow/HLD.md`).
**Correction of an earlier claim in this same investigation:** a first draft of this
entry asserted "there is no deterministic first-pass anchor seeder." **That was wrong.**
A structured raw->anchored conversion process exists and is canonical.

**What actually exists (verified by running it).** `scripts/first_run_readonly.sh HLD.md`
runs `hld_spec_sync.py --hld-format-report` first, auto-detects readiness, and if the HLD
is raw it emits the full **marking path** and stops at stage `CONVERSION_READY_TO_APPLY`:
`logs/.../hld_format_report.md`, `logs/.../suggested_hld_sections.json`,
`.specify/sync/raw_hld_marking_plan.json|md` (one item per section, from
`scripts/build_raw_hld_marking_plan.py` ROLE_KEYWORDS heuristics),
`.specify/sync/hld_conversion_plan.json|md`, `hld_conversion_decision_queue.json|md`,
`RAW_HLD_MARKING_PROMPT.md`, `HLD_CONVERSION_PROMPT.md`. The agent then converts in
bounded 3-5 section batches using `grep`/`rg`/`sed -n`/`awk`, preserving `HLD.raw.md`
(see `docs/FIRST_RUN.md`), and reruns -> HLD map -> Spec Build Plan -> Plan Quality Gate
-> Review (the **slice/build path**). On Baton Flow: the raw run produced 12 marking
items + `PROCEED_CHUNKED_CONVERSION`; the anchored run produced a full `spec_build_plan`
+ SpecKit prework package. The `apply_hld_conversion` machine
(`hldspec/machines/apply_hld_conversion.py`) can apply the decisions. Earlier confusion
came from testing only `classify_hld_sections.py` (which *does* require existing anchors)
and `agent_session --mode create` (which does not route into this flow) — not the
`first_run_readonly.sh` entry point.

**The real gap (two parts).**
1. **Unreconciled entry points.** `agent_session start --mode create` copies the source,
   reports `0 HLD anchors`, and hands a generic `HLD_GENERATION.md` prose prompt — it does
   NOT trigger the `first_run_readonly.sh` readiness-detection/conversion flow. A user who
   enters via `agent_session` never sees the marking plan / conversion prompt / decision
   queue that the documented first-run path provides. These should converge.
2. **Backlog note: the demonstrated legacy run was deleted.** The full worked
   example (`.hldspec-first-run/`
   marking plan, format report, etc.) was removed in commit `9654a5e` ("exclude workspace
   artifacts from repo") for a correct reason (workspace output != repo), but with it the
   *example of the process* was lost — itself an instance of the "vibe dev loses key parts"
   failure mode HLDspec fights. A small fixture/golden under `tests_v2/` or `docs/` should
   preserve a canonical raw->anchored example so it can't silently disappear again.

**Caveat on `raw_hld_marking_plan` quality.** Its role/risk values are keyword-heuristic
DRAFTS, not authoritative: on Baton Flow it tagged Technology, Out-of-scope, and
Extensibility as `governance_context/HIGH` and the lifecycle as `data_model`. The process
intends the agent to correct these via `HLD_CONVERSION_PROMPT.md`; the value of the tool
is the never-skip scaffold (every section gets an item, a decision queue, readiness gating,
`HLD.raw.md` preservation), not finished metadata.

**Minor polish (found by diffing tool output vs hand-anchoring; not blocking).**
1. `apply_hld_conversion_decisions.py` writes titles as `## HLD-001 - 1. What it is` —
   it keeps the source's leading `N. ` ordinal, producing double numbering. It should
   strip a leading `^\d+\.\s` from the title when synthesizing the anchored heading.
2. `apply` defaults almost every section to `HLD-ROLE: architecture` / `HLD-RISK: MEDIUM`
   and does NOT carry through the per-section role guesses already computed in
   `raw_hld_marking_plan.json` (which had governance/data_model/interface_contract/etc.).
   Wiring the marking-plan roles into the apply step would make the scaffold draft a better
   starting point. Neither is urgent: the agent judgment pass corrects both, and "if it's
   good, it's good" — the method works at its job (never-skip scaffold), so this is polish,
   not a rewrite.

**Baton Flow note.** The Baton Flow HLD was anchored by hand (12 sections -> `## HLD-0NN`
+ HLD_FORMAT metadata, prose verbatim) and validates clean (`validation_errors == []`),
with cleaner role assignments than the raw draft. That hand-pass *skipped the scaffold*
(no preserved `HLD.raw.md`, no decision queue) but reached a valid, better-classified
result. For the next HLD, prefer entering through `first_run_readonly.sh` so the scaffold
is not skipped.

## Next safe patch sequence

1. Review GitHub diff and RunSkeptic on this stale-truth update.
2. Wire context validation and promotion checks into guarded product-flow stops.
3. Add end-to-end journey tests through the public facade.
4. Add stale-artifact and diff detection.
5. Add domain validators for backend triggers, principle evidence, constitution purity, package testability, graph/queue parity, and handoff pointers.
6. Propagate RunSkeptic PASS/ACTION/CONFLICT through gate-machine and handoff outputs.
