# RunSkeptic Review — "Single-HLD SpecKit Source-Package" Rewrite Prompt

Read-only RunSkeptic review of the **planned redesign** described in the HLDspec
rewrite prompt, performed *before* any edit, as the prompt itself requires
("perform a read-only RunSkeptic review of the planned redesign ... Identify
ACTION/CONFLICT findings. Do not edit until the redesign is decomposed enough to
be testable").

Final category: **CONFLICT** (4 source-of-truth/ownership conflicts must be
resolved by the Human Decision Owner before implementation can start).

---

## RunSkeptic Receipt

- **Source read:** `/Users/saffi/code/skeptic/skeptic.md` — repo HEAD `4481290b5e7f`,
  file sha256 `c5f60f48a09660e63fb09cf2a464185f928608ba5823fa7284aff6c56e9959bb`.
  Read in full (558 lines). Not a memory/summary substitute.
- **Companion files read:** none. `skeptic-questions.md` not required for this
  design-level review (runtime core is authoritative; external bank only expands
  domain detection).
- **Permission mode:** read-only. No files edited during this review.
- **DONE statement:** "Decide whether the rewrite prompt's planned redesign can be
  implemented as-specified, or whether it contains blocking conflicts/ambiguities
  that must be resolved first; produce a testable decomposition." This DONE is
  testable: the output is a category (HANDLED/CONFLICT) plus an enumerated,
  evidence-backed conflict list and a decomposition where each slice returns to GATE.
- **Major steps run:** GATE, FUNDAMENTAL SCAN, MAP, CONFIDENCE, STABILIZE, EVIDENCE,
  DECIDE. (ACT/VERIFY/LEARN not reached — DECIDE = CONFLICT, so no edits.)
- **Thinkers considered:** CH, OM, FE, PO, KT, SH (all; SH produced a finding).
- **Evidence used:** the rewrite prompt text; `docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md`
  (declared authoritative); `AGENTS.md`; `CLAUDE.md`; `docs/HLDSPEC_DEVELOPMENT_HANDOFF.md`;
  `docs/HLDSPEC_DEVELOPMENT_BACKLOG.md`; `hldspec/state_machine.py`; repo `ls` of
  `hldspec/`, `hldspec/machines/`, `scripts/`, `tests_v2/`; `git log`.
- **Decision path:** GATE → "too large but clear in parts; contains unresolved
  ownership ambiguity" → FUNDAMENTAL SCAN surfaces ownership/SoT conflicts →
  these are not decomposable away → DECIDE = CONFLICT for C1–C4; DECOMPOSE proposal
  attached for the buildable remainder.
- **Verification performed:** each conflict cross-checked against a quoted line in an
  authoritative repo file (see Evidence column). No runtime verification (read-only).
- **Unresolved conflicts / unknowns:** C1–C4 (below). Unknown: which document is
  canonical going forward.
- **Final output category:** CONFLICT.

---

## 0. GATE

- DONE testable? **Yes** (category + conflict list + decomposition).
- Scope tractable? **No, not as a single unit.** The prompt asks for ~16 new modules,
  ~12 new scripts, a 22-state machine, a generated constitution, engineering
  guidelines, runbook, prompts, target `AGENTS.md`, tmux support, and dozens of tests
  — a multi-thousand-line coherent rewrite. Per skeptic GATE, "too large but clear ->
  DECOMPOSE".
- Wrong-answer cost? **High.** It changes ownership of `.specify/` (SpecKit's
  territory), the constitution, and the model-tier taxonomy — foundational
  source-of-truth surfaces.
- Intent/assumptions/approach explicit enough to test? **Partially.** The mechanical
  slices are explicit. But the prompt assumes it may override the repo's declared
  authoritative doc without saying so, which is the central ambiguity.

GATE verdict: **DECOMPOSE the buildable parts; CONFLICT on the ownership/SoT parts.**
Multiple valid interpretations exist (rewrite prompt overrides the canonical doc, or
the canonical doc overrides the prompt, or they merge) — per GATE, proceed only on an
interpretation that is "evidence-backed, low-risk, and testable." None of the three is
yet selected, so the foundational choice must be escalated.

---

## 0.5 / 1. FUNDAMENTAL SCAN + MAP (detect only)

The scan target is the *design*, not code. The invalidating question is **ownership /
source of truth**, because the prompt relocates HLDspec's outputs into SpecKit's
declared territory. If that's wrong, every downstream module path is wrong, so all
module-level findings below are **PROVISIONAL** until the ownership question resolves.

### Conflicts (each cross-checked against an authoritative file)

| # | Rewrite prompt requires | Repo authority (quoted) | Evidence |
|---|---|---|---|
| **C1** | HLDspec generates 9+ files under `.specify/source/` (`HLD.marked.md`, `source_manifest.json`, `source_package.json`, `engineering_guidelines.md`, `speckit_single_spec_input.md`, `speckit_runbook.md`, `runner_prompt.md`, `consultant_prompt.md`, `human_review_package.md`) and treats them as authoritative | `docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md` §2: *"HLDspec control artifacts live in `target/.hldspec/`, **never** in `.specify/`. `target/.specify/` and `target/specs/` are SpecKit-owned."* | OBSERVED |
| **C2** | HLDspec generates/updates `.specify/memory/constitution.md` and target `AGENTS.md` | `AGENTS.md`: *"SpecKit owns: `.specify/memory/constitution.md` updates after approval."* | OBSERVED |
| **C3** | "Only two tiers: `MODEL_SIMPLE` / `MODEL_SMART`" | `CLAUDE.md`, `AGENTS.md`, `docs/HLDSPEC_DEVELOPMENT_HANDOFF.md` all encode **four** tiers: `MODEL_ROUTINE` / `MODEL_DEFAULT` / `MODEL_STRONG` / `MODEL_CRITICAL`, with concrete Codex/Claude/Devin mappings | OBSERVED |
| **C4** | "Do not split the HLD into many SpecKit specs by default" → a single `speckit_single_spec_input.md` | `docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md` §7: Spec Package → **Feature Dependency Graph** → **SpecKit Invocation Queue** is the ordering source of truth; multiple packages is the model. Invariant #7 in CLAUDE.md guards graph/queue parity. | OBSERVED |

### Non-blocking scope/deprecation findings (ACTION, not CONFLICT)

| # | Finding | Evidence |
|---|---|---|
| **A5** | Prompt says "deprecate bundle queue / many-spec / `handoff_docs` as primary review." Repo *just* landed Run Card + handoff centralization (commits `d1149d5`, `6605d6e`, `ae67201`). The canonical doc frames bundle prompts as "Run Card precursors," not deprecated. Deprecating freshly-built, tested code is a regression risk unless replaced + tested in the same change. | OBSERVED |
| **A6** | New modules (`speckit_workspace.py`, `hld_source_package.py`, `hld_marking.py`, `hld_patch.py`, `single_spec_input.py`, `state_machine.py`, …) overlap existing `spec_bundles.py`, `speckit_run_card.py`, `handoff_docs.py`, `speckit_execution_state.py`, `state_machine.py`. The prompt does not say replace-vs-augment per module. `state_machine.py` already exists with 5 statuses + 6 checkpoint kinds; the prompt's 22-state machine is a different shape. | OBSERVED |
| **A7** | Tmux/session-manager is made a *hard requirement* with a required runbook diagram. It appears nowhere in the canonical flow and is orthogonal to the existing orchestrator/junior model. Buildable, but it's net-new surface, not a conflict. | OBSERVED |
| **A8** | The prompt's mental model ("HLD → many specs → invocation queue → bundle queue → bundle prompts → handoff docs" as the *old* model to deprecate) is partly stale: the repo already moved toward a single Run Card model (canonical doc §8, recent commits). Parts of the rewrite are already done. | OBSERVED |

---

## 2–3. Universal Questions + Thinkers (applied to the design)

- **Universal:** *What is the source of truth for the target's product spec, and who
  owns `.specify/`?* The prompt answers "`.specify/source/` (HLDspec-written)"; the
  repo answers "`target/.hldspec/` for HLDspec, `.specify/` for SpecKit." Two
  competing source-of-truth answers = the core defect.
- **CH (dependencies/failure):** If HLDspec writes into `.specify/`, then a later
  `specify init` or SpecKit regeneration in the target can overwrite or fight
  HLDspec's files — two writers, one directory, no declared arbiter. Failure is *not*
  bounded; it corrupts the authoritative source package. This is the strongest
  finding.
- **OM (necessity/boundaries):** The single-input model (C4) is *simpler* than the
  graph+queue model and may be the right call — but it deletes the graph/queue
  parity invariant that other code and tests depend on. Removing it: graph/queue
  parity tests break; ordering SoT disappears. "Remove this, what breaks?" → real
  breakage, so it cannot be a silent default.
- **FE (honesty):** Is "only two tiers" true/better now? Not demonstrably — the
  4-tier model carries concrete vendor mappings the 2-tier model drops. The change is
  asserted, not justified.
- **PO (falsification):** What proves the `.specify/source/` design unsafe? A target
  where SpecKit `init` or a SpecKit phase rewrites `.specify/` and silently clobbers
  HLDspec's `source_package.json`. No test or guard is specified to detect this.
- **KT (universalizability):** "Tool writes into another tool's owned directory" — do
  we want that pattern everywhere? No; it's exactly the ownership-blur the canonical
  doc was written to forbid. Narrow or relocate.
- **SH (integration vs compromise):** Real forces = (A) "keep the approved package
  physically next to SpecKit so the runner has one place to look" vs (B) "keep
  HLDspec control state out of SpecKit-owned space so neither tool clobbers the
  other." The prompt's `.specify/source/` is a *compromise* that keeps both costs
  (co-location AND ownership collision). A real *integration* would be: HLDspec owns
  `target/.hldspec/source_package/`, and the import step produces a SpecKit-consumable
  read-only artifact (or symlink/copy) the runner reads — ownership stays clean,
  co-location is achieved at handoff. **Recommendation: side B (clean ownership)
  should dominate as default; the narrow exception is a generated, clearly-derived,
  read-only mirror under `.specify/` if the runner truly needs it there.**

---

## 6. Detection Confidence

- Fundamental Scan completed: yes.
- Universal Questions applied: yes.
- All Thinkers considered: yes (CH, OM, FE, PO, KT, SH); SH produced a finding.
- Structural Checks: applied (ownership, SoT, competing copies, boundaries).
- Domain Checks: ARC (architecture/ownership) primary; CFT (tests/regression) for A5.
- Confidence: **high** for C1–C4 and A5–A8 — each is a direct, quoted contradiction
  between two documents both currently in the repo. No inference required.
- Blind spots: I did not read every one of the 85 scripts or 63 test files; A6's
  replace-vs-augment mapping is therefore INFERRED at the per-file level (the conflict
  itself is OBSERVED).

---

## 7. STABILIZE

Findings merge into **one root cause**: *the rewrite prompt was written against an
older mental model of HLDspec and silently assumes authority to override the repo's
declared-authoritative `docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md` on ownership, the
constitution, model tiers, and the single-vs-many spec model.* C1, C2, C4 are all the
same "who owns the source of truth, and where does it live" issue. C3 is an
independent taxonomy conflict. A5–A8 are scope/regression consequences of the same
stale-model root cause.

Root-cause class: **source-of-truth issue** + **stale assumption** (skeptic §7).

---

## 8. Evidence Levels

- C1, C2, C3, C4: **OBSERVED** (direct doc-vs-doc contradiction, quoted).
- A5, A7, A8: **OBSERVED**.
- A6 per-file replace/augment mapping: **INFERRED RISK** (conflict OBSERVED, mapping
  not yet read file-by-file).
- CH "two writers clobber `.specify/`" failure: **INFERRED RISK** (structurally
  plausible, not reproduced — no target run executed).

---

## 9. DECIDE → CONFLICT

Per skeptic §9, choose one path per stabilized issue.

- **C1–C4: CONFLICT.** These require product/architecture intent and source-of-truth
  ownership decisions. The skeptic framework forbids silently resolving them, and the
  canonical doc explicitly says it "wins on any conflict." Decomposition does **not**
  remove the ambiguity — it's a genuine design choice, not a sizing problem.
- **A5–A8: deferred ACTION**, contingent on the C-decisions. Once direction is set,
  each becomes a bounded FIX with a regression test.

### CONFLICT items (skeptic §13 format)

**CONFLICT-C1: where does HLDspec's approved source package live?**
- Thesis (prompt): under target `.specify/source/`, co-located with SpecKit, so the
  runner reads one place.
- Antithesis (canonical doc): HLDspec never writes `.specify/`; control state lives in
  `target/.hldspec/`; `.specify/` is SpecKit-owned.
- Tradeoffs: co-location/runner-simplicity vs ownership-collision/clobber-risk.
- Blocking unknown: is the `.specify/source/` subdir contractually safe from SpecKit
  init/regeneration, or does SpecKit treat all of `.specify/` as its own?
- Missing evidence: behavior of the chosen SpecKit `init` on a pre-existing
  `.specify/source/`.
- Safe recommendation: HLDspec owns `target/.hldspec/source_package/`; the import step
  materializes a **derived, read-only** copy into `.specify/source/` if needed,
  clearly marked generated. Keeps the canonical invariant intact while satisfying the
  runner-co-location goal.
- Decision needed: **human.**

**CONFLICT-C2: who authors `.specify/memory/constitution.md`?**
- Thesis (prompt): HLDspec generates/updates it with 12 mandatory principles.
- Antithesis (AGENTS.md): SpecKit owns constitution updates *after approval*.
- Safe recommendation: HLDspec generates a **constitution proposal/guidance** artifact
  it owns; SpecKit (or an approval gate) applies it to `.specify/memory/`. Matches the
  existing `constitution_update_plan.py` pattern.
- Decision needed: **human.**

**CONFLICT-C3: 2 model tiers or 4?**
- Thesis (prompt): collapse to `MODEL_SIMPLE` / `MODEL_SMART`.
- Antithesis (3 repo docs): keep `MODEL_ROUTINE/DEFAULT/STRONG/CRITICAL` with vendor
  maps.
- Safe recommendation: keep 4 canonical tiers; if a 2-tier *view* is wanted for
  runner/consultant packets, define SIMPLE = {ROUTINE} and SMART = {STRONG, CRITICAL}
  as a derived projection, not a replacement.
- Decision needed: **human.**

**CONFLICT-C4: single SpecKit input vs many packages + graph/queue?**
- Thesis (prompt): one `speckit_single_spec_input.md`; do not split by default.
- Antithesis (canonical §7 + invariant #7): packages → dependency graph → invocation
  queue is the ordering SoT.
- Tradeoffs: single-input simplicity & "let SpecKit/clarify discover boundaries" vs
  losing dependency-ordered execution and the parity invariant other code/tests rely
  on.
- Safe recommendation: support a single-input mode as the *default for one coherent
  HLD*, but retain the package/graph/queue model as the path when boundaries are
  already known; do not delete the parity invariant or its tests.
- Decision needed: **human.**

---

## Proposed decomposition (once C1–C4 are decided)

Each slice returns to GATE; each is independently testable in `tests_v2/`.

1. **Source-package shape & ownership** — model + manifest + `source_package.json`
   under the *decided* location; validator for required files; failure tests.
2. **HLD marking & reference map** — stable anchors, duplicate-anchor rejection,
   `hld_reference_map.json` (anchor/heading/hash).
3. **Single-spec input generation** — cites anchors, flags unsupported claims,
   preserves open questions; mode-flag vs package model per C4.
4. **Constitution guidance + engineering guidelines** — per C2 (proposal vs direct
   write); required-principle and required-section tests.
5. **Runbook + runner/consultant prompts** — Context Receipt, Phase Report, stop
   conditions, model routing per C3, tmux/session block (A7).
6. **Target AGENTS.md generation** — required reads, source authority, no
   self-approval, receipt-before-acting.
7. **Gate validator** — blocks missing receipt / stale anchors / missing refs /
   missing RunSkeptic PASS / Consultant BLOCK / unsupported claims.
8. **HLD diff + stale check** — hash-based stale detection, change-impact.
9. **Session control** — main-controller / basepack / runner / consultant roles +
   bounded subagent task packets.
10. **State machine** — reconcile the proposed 22 states with existing
    `state_machine.py` (extend, don't fork) per A6.
11. **Legacy deprecation + regression tests** — per A5/A8: mark legacy off-by-default
    *with* a test proving the new default path doesn't use the bundle flow, and *with*
    the replacement landed in the same change.

---

## Next safe action

Escalate C1–C4 to the Human Decision Owner (one decision each). Do **not** edit code
until the ownership/SoT direction is chosen, because the chosen direction determines
every module's output path and the replace-vs-augment decision for ~6 existing
modules. After the decision, implement slice 1 first (smallest, most foundational),
returning to GATE per slice.

---

## RESOLUTION (Human Decision Owner, 2026-05-27)

Direction chosen: **Hybrid (RunSkeptic safe-rec).** Adopt the rewrite prompt's
direction, apply the RunSkeptic safe recommendation wherever it collides with an
ownership invariant, then update the canonical doc to match.

- **C1 + C2 — RESOLVED (safe-rec).** HLDspec owns
  `target/.hldspec/source_package/` (the approved source package). The import step
  materializes a **derived, clearly-generated, read-only mirror** into
  `target/.specify/source/` for the runner. The canonical invariant "HLDspec never
  *authors* into `.specify/`" holds: the mirror is generated/derived, not authored,
  and is regenerated from `.hldspec/`. The constitution is authored by HLDspec as a
  **proposal** (`constitution.proposed.md` under `.hldspec/source_package/`) and is
  applied to `.specify/memory/constitution.md` only at `CONSTITUTION_APPROVAL_GATE`.
- **C3 — RESOLVED (KISS).** Operational taxonomy is **two tiers**:
  `MODEL_SIMPLE` / `MODEL_SMART`. A documented, lossless mapping to the four
  canonical tiers is retained (`SIMPLE ← ROUTINE`; `SMART ← DEFAULT/STRONG/CRITICAL`)
  so the set can expand when a concrete need appears. Pragmatic, not rigid.
- **C4 — RESOLVED (single default + meaningful layering).** A **single** SpecKit
  input is the default for one coherent HLD. Optional **value-based layers/steps**
  (e.g., an infra MVP layer) are supported when a slice is large enough *and*
  independently valuable — sliced by meaningful boundaries (source-of-truth,
  architecture, dependency, deployable value), **never** by line count. The
  package/graph/queue parity invariant and its tests are **retained** for the
  layered path; they are not deleted.

A5–A8 become bounded ACTIONs under this direction: legacy bundle/many-spec flow is
marked off-by-default *with* a regression test proving the new default path, landed
in the same change; new modules **extend** existing ones (notably `state_machine.py`)
rather than fork them.

Build order (each slice returns to GATE, tested in `tests_v2/`): see decomposition
slices 1–11 above; slice 1 (workspace layout + source-package shape + ownership) is
foundational and goes first.
