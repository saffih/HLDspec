# Journey 3 — Helper Contract

**Status:** product contract. This is the testable contract for Journey 3 of the
three-journey model (`docs/THREE_JOURNEYS.md`). It defines how Journey 3 consumes
a Journey 2 target package, installs a selected **helper** into the target repo,
and guides the **targeteer** to implementation completion — with **SpecKit as one
helper, not the definition of Journey 3**.

Like the Journey 1 and Journey 2 contracts, this documents and hardens
**already-implemented** mechanics. The phase/run-card engine lives in
`hldspec/next_feature_readiness.py`; the target-local runtime is vendored by
`hldspec/refresh_target.py` (commit *vendor self-contained Journey 3 run-card
runtime*). This doc is their binding contract, not a new mechanism.

> Status update: `helper_recommendations` is **now emitted by Journey 2**
> (`hldspec/hld_source_package.py::build_helper_recommendations`) to
> `target/.hldspec/source_package/helper_recommendations.json`. Journey 3 has
> selected-helper state at `.hldspec/helper_selection.json`
> (`hldspec/helper_selection.py`), surfaced via the `## Toolchain` status section
> and the `select-helper` CLI command. §8 and §13 define the seam and the
> remaining gaps.

> **New helper onboarding:** when a new tool/skill is introduced as a candidate
> helper, it enters through the Generic Helper Bootstrap
> (`docs/HELPER_BOOTSTRAP_CONTRACT.md`). The Bootstrap generates a candidate
> HelperContract; this doc defines the operational contract that a Bootstrap
> graduate fills when it reaches `OPERATIONAL_HELPER`.

---

## 1. Purpose

Journey 3:
- consumes the **PASSed** Journey 2 target package;
- installs / materializes a **selected helper** into the target repo;
- guides the human/targeteer through the selected toolchain until implementation
  completion — showing the **path to done**, one safe step at a time.

It is a **consumer and operator**, not a synthesizer.

## 2. Input

- A Journey 2 target package at `target/.hldspec/source_package/` that **PASSed**
  `SOURCE_PACKAGE_APPROVAL_GATE` (see `docs/JOURNEY2_PACKAGE_CONTRACT.md`).
- A **selected helper**, or the safe default (`helper: speckit`).
- The **target repo** (git working tree).

Journey 3 must **refuse** a package that did not PASS Journey 2. It never compiles
or repairs the package.

## 3. Output — the helper runtime

Materialized into the target repo (today, by `refresh-target --apply`):

| Output | Existing realization |
|---|---|
| **Helper runtime** | `.hldspec/runtime/` (vendored, stdlib-only) + `.hldspec/bin/run-card` wrapper. Self-sufficient: runs with `HLDSPEC_HOME` unset; read-only. |
| **Run card** | The `next_feature_readiness` report: exactly one `phase`, blockers, allowed/forbidden actions, the single next safe SpecKit step. |
| **Completion map** | The phase model (§9) — the full setup→done path, not just "what now". |
| **Stop rules** | Per-phase stop conditions; the runtime stops at any ACTION/BLOCKED phase and at the implementation-approval boundary. |
| **Model/agent guidance** | Model-tier guidance for each step (routine vs strong vs critical). |
| **Report-back protocol** | The fixed report shape: new phase, new blockers, `[NEEDS CLARIFICATION]`, RunSkeptic status, whether HLDspec should reassess. |
| **Helper-specific operating instructions** | The `speckit` runbook / runner prompt / slice execution prompt carried in the package. |

## 4. What Journey 3 must not do

- **No HLD authoring** (Journey 1).
- **No feature decomposition** (Journey 2).
- **No spec synthesis** — it consumes `speckit_single_spec_input.md`, never writes it.
- **No constitution invention** — it consumes `constitution.proposed.md`; SpecKit owns the applied constitution.
- **No package repair** — a wrong package returns to Journey 2; a wrong HLD to Journey 1.
- **No silent tool execution** — it proposes commands; it does not run SpecKit/build silently.
- **No commit / merge / push** without explicit human approval.

If Journey 3 ever needs upstream truth to proceed, that is a **BLOCKED**, not a
license to invent it.

## 5. Reclassification — the existing SpecKit runtime is `helper_id: speckit`

The self-contained run-card runtime (`next_feature_readiness` + the vendored
`.hldspec/runtime/` + `.hldspec/bin/run-card`) is **the first helper
implementation**: `helper_id: speckit`. It is the proof the Journey 3 shape works,
not the shape itself. Nothing about it changes here — it is reclassified
conceptually, not modified.

## 6. HelperContract

Every helper (current or future) must **declare** the following. The `speckit`
column shows the existing realization; other helpers are **not implemented**.

| Field | Meaning | `speckit` (today) |
|---|---|---|
| `helper_id` | Stable identity | `speckit` |
| `supported_toolchain` | Harness it drives | SpecKit (`/speckit-*` installed commands) |
| `required_package_fields` | Package inputs it needs | `speckit_single_spec_input.md`, `constitution.proposed.md`, slices |
| `required_target_evidence` | Target-repo evidence it reads | git state, `.specify/memory/`, `specs/<branch>/` artifacts |
| `recommendable_commands` | Commands/prompts it may *recommend* | `/speckit-specify`, `/speckit-clarify`, `/speckit-plan`, `/speckit-tasks`, `/speckit-analyze`, slice prompts |
| `must_ask_before_proceeding` | Human-owned questions it must raise | architecture / source-of-truth / scope / `[NEEDS CLARIFICATION]` |
| `completion_map_stages` | Its stage set | the phase model (§9) |
| `stop_rules` | Conditions that force a stop | ACTION/BLOCKED phase, failed tests, human-owned question, RunSkeptic ACTION/CONFLICT, scope expansion |
| `model_agent_guidance` | Model-tier guidance per step | per-step routine/strong/critical guidance |
| `evidence_requirements` | What proves a step done | durable repo evidence only (never chat history) |
| `report_back_format` | Fixed report shape | new phase / blockers / clarification / RunSkeptic / reassess? |
| `final_completion_criteria` | What "done" means | merged/PR-ready with tests + approvals |
| `authority_level` | How far it may act | `GUIDE_ONLY` / `PROPOSE_COMMAND` (§7) |

The same fields, filled differently, are how `claude-code` / `codex` / `devin` /
`manual` would be added later — **without re-solving synthesis** (KT: the pattern
universalizes).

## 7. Helper authority levels

| Level | Meaning | Status |
|---|---|---|
| `GUIDE_ONLY` | Reports phase, evidence, next safe action. Runs nothing. | **current default** |
| `PROPOSE_COMMAND` | Bakes the exact next command/prompt for the human to run. | **current default** |
| `EXECUTE_WITH_APPROVAL` | May run a step **after** explicit human approval per step. | exists opt-in (the live `SpecKitInvoker` / `SpecKit drive` loop); **not** the Journey 3 default |
| `AUTONOMOUS_WITH_GUARDS` | Runs unattended within guards. | **future only — not allowed now** |

**Default for current Journey 3: `GUIDE_ONLY` / `PROPOSE_COMMAND`.** The vendored
runtime is read-only (build + render only; no report persistence, no git/SpecKit/
product mutation), which is exactly these two levels.

## 8. `helper_recommendations` seam (now emitted)

**Where it should live:** `target/.hldspec/source_package/helper_recommendations.json`
(adjacent to the package; keeps `source_package.json` focused on binding metadata).

**Suggested fields:**
- `recommended_helpers` — ordered list of fit helper_ids.
- `default_helper` — the safe default if the human does not choose.
- `rationale` — why these, evidence-based.
- `required_capabilities` — capabilities the package needs from a helper.
- `package_fit` — per-helper fit against the package.
- `target_fit` — per-helper fit against the target repo/toolchain.
- `unsupported_helpers` — helpers that cannot serve this package, with reasons.
- `human_override_allowed` — whether the human may override the recommendation.

**Current behavior:** Journey 2 emits `helper_recommendations.json` per the
fields above. Journey 3 reads it via `hldspec/helper_selection.py` to determine
the recommended default. `select-helper --use-recommended` writes the chosen
`helper_id` to `.hldspec/helper_selection.json`, validated against
`helper_registry.operational_helpers()`.

**Behavior when missing or stale:** Journey 3 **defaults to `helper: speckit`**
and records that no (or no current) recommendation was present. This is an
**ACTION-class** condition (defaultable), never a silent PASS.

## 9. CompletionMap

Journey 3 shows the **path to completion**, not only the current step. The stages
below map 1:1 to `next_feature_readiness` phases (the engine that already exists):

| Stage | Phase (existing) |
|---|---|
| setup | `NEEDS_SPECKIT_INIT` |
| package accepted | Journey 2 PASS (precondition) |
| helper selected | helper selection / default (§8) |
| helper installed / materialized | `refresh-target --apply` vendoring |
| toolchain: constitution | `NEEDS_CONSTITUTION` |
| toolchain: specify | `READY_FOR_SPECKIT_SPECIFY` → `SPEC_BRANCH_BOUND` |
| toolchain: clarify | `NEEDS_CLARIFY_OR_CHECKLIST` |
| toolchain: plan | `READY_FOR_PLAN` → `PLAN_READY` |
| toolchain: tasks | `READY_FOR_TASKS` → `TASKS_READY` |
| toolchain: analyze | `READY_FOR_ANALYZE` → `ANALYZE_READY` |
| implementation | `READY_FOR_IMPLEMENT` → `IMPLEMENTATION_REVIEW_REQUIRED` |
| tests / evidence | execution evidence read per phase |
| commit readiness | `READY_FOR_COMMIT` |
| merge / PR readiness | `READY_FOR_PUSH_OR_PR` / `MERGE_BLOCKED_PENDING_CI_OR_APPROVAL` |
| done | all stages DONE |

Each stage carries:
- `status`: `DONE` / `CURRENT` / `NEXT` / `BLOCKED` / `UPCOMING`,
- `evidence` — the durable repo evidence proving the status,
- `next_safe_action` — the single safe step,
- `done_when` — the completion condition,
- `do_not_run_yet` — what must not be run before this stage,
- `report_back` — what to report after the step.

Phase is derived **only from durable repo evidence**, never chat history — the same
repo state always yields the same phase (reproducible).

## 10. Gate states — PASS / ACTION / BLOCKED

| Gate state | Meaning | Trigger |
|---|---|---|
| **PASS** | Journey 3 can guide the human safely toward completion. | Package PASSed Journey 2; helper selected or safely defaulted; helper runtime installed/materialized; run-card/completion-map can guide; no upstream synthesis required. |
| **ACTION** | Fixable before guidance continues. | Helper selection missing but defaultable; target runtime stale/missing but refreshable; target evidence incomplete but fixable; package valid but helper needs a human answer before the next step. |
| **BLOCKED** | Journey 3 cannot proceed. | Package did **not** PASS Journey 2; helper requires fields not present; target state contradicts the package; unresolved human-owned product/architecture decision; unsafe git/tool state; helper would need to invent upstream truth. |

**Rule:** ACTION is fixed inside Journey 3 (default a helper, refresh the runtime,
ask the human a bounded question). BLOCKED returns **upstream** (Journey 2 for a
bad package, Journey 1 for a bad HLD) — Journey 3 never patches around it.

## 11. RunSkeptic questions for Journey 3

- **CH (inversion):** If Journey 3 starts synthesizing upstream truth, what
  breaks? Two sources of truth diverge with no owner; upstream gates become
  decorative; failures stop being attributable. The §4 must-not list + BLOCKED-on-
  missing-fields bound it.
- **OM (parsimony):** Is `HelperContract` too broad? Each field maps to a real
  failure mode (missing input, missing evidence, unbounded authority, no stop
  rule, no report). Drop one and a known failure reopens.
- **FE (mechanism):** Can a targeteer/agent see *how* Journey 3 works? Phase is
  derived from named repo evidence; the completion map shows the whole path; the
  run card names exactly one next step.
- **PO (refutation):** Can an invalid package/helper pass silently? No: non-PASS
  package → BLOCKED; helper missing required fields → BLOCKED; missing
  recommendation → ACTION with recorded default, not silent PASS.
- **KT (universalizability):** Is the helper pattern safe repeated for speckit,
  claude-code, codex, devin, manual? Yes — each declares the same HelperContract;
  authority stays GUIDE_ONLY/PROPOSE_COMMAND by default for all.
- **SH (tradeoff):** "Drive fully" vs "human stays decision-maker" — resolved with
  a dominant default (GUIDE_ONLY/PROPOSE_COMMAND, human approves every act) and a
  narrow opt-in exception (EXECUTE_WITH_APPROVAL), with AUTONOMOUS_WITH_GUARDS
  refused now. No fake middle.

## 12. Vocabulary bridge

| Framing name | Existing repo realization |
|---|---|
| helper runtime | `.hldspec/runtime/` + `.hldspec/bin/run-card` (vendored) |
| run card | `next_feature_readiness` report |
| completion map | `next_feature_readiness` phase model |
| targeteer | the human/agent completing work in the target repo |
| helper / `helper_id: speckit` | the existing run-card runtime |
| install / materialize helper | `refresh-target --apply` |
| helper_recommendations | emitted by Journey 2 — §8 seam |

## 13. Known limits (honest scope)

- **Only one helper exists** (`speckit`). `HelperContract` is the shape future
  helpers fill; no second helper is implemented here, by design.
- **`helper_recommendations` is now emitted** by Journey 2
  (`hldspec/hld_source_package.py::build_helper_recommendations`). Journey 3 may
  read `source_package/helper_recommendations.json` to determine the recommended
  default helper. **The selected helper state is now implemented**:
  `.hldspec/helper_selection.json`, written/read by `hldspec/helper_selection.py`
  and surfaced in `scripts/hldspec_agent_session.py status` (`## Toolchain`
  section) and `select-helper` (writer). Selection validates against
  `helper_registry.operational_helpers()` — a planned-but-not-implemented helper
  id is rejected. See `docs/TOOLCHAIN_DRIVER_BOUNDARY.md`.
- **`helper_id` is not yet a stored field.** The runtime is implicitly speckit;
  formalizing a `helper_id` in the runtime/manifest is a small future change, not
  claimed as present.
- The completion map is **read-only guidance**: it reports and proposes; it does
  not execute, commit, or merge. EXECUTE_WITH_APPROVAL is the opt-in exception,
  not the Journey 3 default.

## 14. Minimal test / validation strategy

**Automated (existing seams):**
- `tests_v2/test_next_feature_readiness.py` — phase derivation from repo evidence.
- `tests_v2/test_refresh_target.py` — runtime vendoring / self-sufficiency,
  read-only, no product/git mutation.
- Doc-contract tests (`tests_v2/test_hldspec_concept_docs.py`,
  `test_terminology_and_flow_docs.py`) keep index/canonical doc aligned.

**Manual checklist** (per target):
1. Package PASSed Journey 2 before any Journey 3 step.
2. Helper selected, or default `speckit` recorded with the missing-recommendation note.
3. `.hldspec/runtime/` + `.hldspec/bin/run-card` present and self-sufficient.
4. Run card names exactly one next safe action and the matching stop rule.
5. No commit/merge/push proposed without an explicit human-approval gate.
6. Any need for upstream truth → BLOCKED returned upstream, not invented.
