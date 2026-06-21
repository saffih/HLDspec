# Journey 2 — Architecture Package Authoring Path (read-only report)

**Status:** read-only analysis. This report changes **no code behavior**. It exists
to make the next Journey 2 decision reviewable without local terminal context.

**Report question:** What is the smallest *safe* authoring path for
`architecture_package.json` that fills HLD-grounded fields **without inventing
architecture truth**?

**Headline answer (up front):** Of the 14 required fields, **exactly one is
machine-DERIVABLE today — `helper_recommendation` — and it is already emitted.**
The remaining 13 are human architecture/product judgment (`HUMAN_OWNED` /
`DO_NOT_DERIVE`) or structural placeholders (`SCAFFOLD_ONLY`). There is **no safe
automated path that fills the reasoning fields from HLD evidence**. Recommendation:
**DO_NOT_PATCH** the derive-into-fields approach; keep the artifact advisory and
ACTION-until-human-authored; keep gating deferred.

---

## 1. `main` SHA inspected

`507b398def57cc9aca560f8bd59bc805f2503e44` (origin/main, fast-forward clean).
PR #25 merge present: `Merge pull request #25 … journey2-architecture-package-emission`
(parents `5f8aee3` + `765171c`). PR #24 (non-stateful readiness) also present.
Working tree clean; **no local/uncommitted work influenced this report** — all
evidence is from committed files on `main @ 507b398`.

## 2. Files read (on `main @ 507b398`)

Docs: `docs/THREE_JOURNEYS.md`, `docs/JOURNEY1_SDD_READY_GATE.md`,
`docs/JOURNEY2_PACKAGE_CONTRACT.md`, `docs/JOURNEY2_ARCHITECTURE_PACKAGE_CONTRACT.md`,
`docs/JOURNEY3_HELPER_CONTRACT.md`.
Code: `hldspec/journey2_architecture_package.py`, `hldspec/hld_source_package.py`,
`hldspec/hld_marking.py`, `hldspec/single_spec_input.py`,
`hldspec/implementation_slicing.py`, `hldspec/engineering_selection.py`,
`hldspec/gate_validator.py`.
Tests: `tests_v2/test_journey2_architecture_package.py`,
`tests_v2/test_source_package.py`.

## 3. Current state on `main`

- `hldspec/journey2_architecture_package.py` defines the 14-field shape, a pure
  `validate_architecture_package`, **and** (since PR #25) a pure
  `build_architecture_package(*, helper_recommendation=None)` that materializes the
  typed slot: only `helper_recommendation` grounded (injected), the other 13 fields
  emitted **empty** → the artifact validates **ACTION** until authored.
- `hldspec/hld_source_package.py::build_source_package_content` emits
  `architecture_package.json` into `target/.hldspec/source_package/`. It is in
  `AUTHORITATIVE_FILES` (manifest-hashed), in `_MIRROR_EXCLUDED` (kept out of
  `.specify/source/`), **not** in `REQUIRED_FILES`, and **not** referenced by
  `gate_validator.py`. So `validate_source_package().ok()` and
  `SOURCE_PACKAGE_APPROVAL_GATE` are unaffected; a missing/ACTION artifact blocks
  no promotion.
- Net: the typed slot is **emitted but unauthored**. The open question is the
  authoring path for the 13 empty fields.

## 4. The 14 fields — classification

Buckets:
- **DERIVABLE** — a machine can fill it *faithfully* from an existing artifact
  without judgment or paraphrase.
- **HUMAN_OWNED** — needs architecture/product judgment; **safe to leave empty with
  an evidence *pointer***; auto-filling would paraphrase/guess.
- **SCAFFOLD_ONLY** — only a structural placeholder is safe; must stay ACTION until
  authored.
- **DO_NOT_DERIVE** — auto-filling would **invent source-of-truth / convert an
  assumption into a fact** (the CH:SO failure `THREE_JOURNEYS.md` §5 names). Stronger
  than HUMAN_OWNED: not even a derived draft is safe.

| # | Field | Class |
|---|---|---|
| 1 | `product_goal_summary` | HUMAN_OWNED |
| 2 | `architecture_intent` | DO_NOT_DERIVE |
| 3 | `source_of_truth_map` | DO_NOT_DERIVE |
| 4 | `ownership_boundaries` | DO_NOT_DERIVE |
| 5 | `contracts_and_seams` | HUMAN_OWNED |
| 6 | `brownfield_constraints` | HUMAN_OWNED |
| 7 | `expert_lenses_applied` | SCAFFOLD_ONLY |
| 8 | `domain_assumptions` | DO_NOT_DERIVE |
| 9 | `slice_roadmap` | HUMAN_OWNED |
| 10 | `next_slice_packet` | SCAFFOLD_ONLY |
| 11 | `test_strategy` | HUMAN_OWNED |
| 12 | `forbidden_shortcuts` | HUMAN_OWNED |
| 13 | `growth_and_change_notes` | HUMAN_OWNED |
| 14 | `helper_recommendation` | DERIVABLE (already emitted) |

Tally: **DERIVABLE 1**, SCAFFOLD_ONLY 2, HUMAN_OWNED 7, DO_NOT_DERIVE 4.

## 5. DERIVABLE fields — source, evidence, failure mode

**Only `helper_recommendation` (14).**
- **Source:** `hldspec/hld_source_package.py::build_helper_recommendations`, derived
  from `hldspec/helper_registry.py` (`implemented_helpers`, `PLANNED_HELPER_IDS`,
  `default_helper_id`, `registry_sha256`). Injected into
  `build_architecture_package(helper_recommendation=…)`.
- **Evidence/anchor requirement:** the helper registry (not the HLD). It is *not*
  HLD-architecture-derived — it is capability metadata. This is **why its
  derivability does not generalize** to the other 13 fields (see §14).
- **Failure mode if evidence missing:** registry always contains `speckit`; an empty
  registry would yield an empty recommendation, but the field stays advisory and
  value-agnostic to the verdict, so no false architecture claim is produced.

No other field is DERIVABLE. The richest *faithful* HLD signal,
`hld_marking.build_reference_map` (anchors → `HLD-ROLE`/`HLD-RISK`/`HLD-STATUS`/
lines/sha256), is **section metadata, not architecture intent** — it can *point* a
human at sections but cannot *state* the architecture without judgment.

## 6. HUMAN_OWNED fields — why not derivable, what input is needed

For each: a **pointer** to HLD evidence is safe; an **auto-paraphrase of that
evidence into the field value is not** (that is the invention line).

- **`product_goal_summary` (1)** — Summarizing product intent in product terms is
  judgment; the HLD purpose/scope section is prose, and paraphrasing it risks
  distortion. *Pointer:* anchor IDs whose `HLD-ROLE` is purpose/scope/requirement.
  *Needs:* a human one-line product goal.
- **`contracts_and_seams` (5)** — The seams to establish *before* behavior are a
  design decision. `engineering_guidelines.md` names *generic* seam guidance, not
  this HLD's contracts. *Needs:* human-named interfaces/seams grounded in the HLD.
- **`brownfield_constraints` (6)** — The HLD may *state* constraints, but which are
  binding on the design is judgment. *Pointer:* `HLD-RISK`/constraint anchors and
  `engineering_selection.detect_engineering_triggers` hits. *Needs:* human selection
  of the real existing-system constraints.
- **`slice_roadmap` (9)** — **Provably not derivable from existing slices.**
  `implementation_slicing.DEFAULT_SLICES` are a *generic, hardcoded* policy
  (FOUNDATION/WALKING_SKELETON/DOMAIN_MODEL/…) with schema
  `{name, purpose, allowed_work, forbidden_work, required_tests}` — **not** the
  architecture-package slice schema (missing `layer`, `expected_files_or_areas`,
  `dependency_ids`, `risk_level`, **`rollback_story`**, **`architecture_value`**).
  Mapping them would *fabricate* rollback stories and architecture-value claims.
  *Needs:* human-authored reviewable slices.
- **`test_strategy` (11)** — Architecture-level evidence strategy is judgment.
  *Pointer:* `implementation_slicing.render_slice_test_policy` (`slice_test_policy.md`)
  and engineering quality-gate markers. *Needs:* human strategy across slices.
- **`forbidden_shortcuts` (12)** — *This design's* ruled-out traps are design
  reasoning. Generic traps ("brittle MVP", "premature optimization") are doc-generic,
  not HLD-grounded, so seeding them would not be evidence-based. *Needs:* human.
- **`growth_and_change_notes` (13)** — How the design absorbs growth without
  premature optimization is architecture judgment with no faithful source. *Needs:*
  human.

## 7. DO_NOT_DERIVE fields — why auto-fill is unsafe

These would not merely be low-quality if auto-filled; they would **manufacture
product/architecture truth** the HLD/human did not decide
(`JOURNEY2_PACKAGE_CONTRACT.md` §8; `THREE_JOURNEYS.md` §5 `CH:SO`):

- **`architecture_intent` (2)** — The intended shape *and why* is the core
  architecture decision. No deterministic extractor exists; any auto-value is invented.
- **`source_of_truth_map` (3)** — Where each truth lives / no split ownership. The
  reference map's `HLD-ROLE` is *section role*, not data SoT. Deriving SoT is the
  worst-case failure (two diverging sources of truth, no owner).
- **`ownership_boundaries` (4)** — Which component owns which responsibility — a human
  decision; section role ≠ module ownership.
- **`domain_assumptions` (8)** — Stated so they can be *challenged*. Auto-deriving
  assumptions would **convert weak assumptions into facts** (explicitly forbidden),
  defeating the field's purpose.

## 8. SCAFFOLD_ONLY fields — safe placeholder, why ACTION

- **`expert_lenses_applied` (7)** — The lens *vocabulary*
  (`BUILTIN_EXPERT_LENSES`: software_architecture, brownfield_integration, …) is
  derivable as a **checklist of keys**, but the lens *findings* are reasoning. Safe
  placeholder: the lens keys with **empty findings**. Because the field must be
  non-empty to PASS, an empty-findings scaffold keeps the package **ACTION** — correct,
  since no real lens review has happened.
- **`next_slice_packet` (10)** — A **descriptive** pointer to the next slice. Until
  `slice_roadmap` is authored there is no next slice, so the safe placeholder is an
  **empty descriptive dict** (today's emitted `{}`). It must remain ACTION until
  authored, and must stay **descriptive data only** — never a `NextActionPacket` /
  `READY` / execution channel (`JOURNEY2_ARCHITECTURE_PACKAGE_CONTRACT.md` §3).

## 9. Authoring-model options

**Option A — derive inside `build_source_package_content()`.**
Auto-fill fields at emission time. *Rejected:* only `helper_recommendation` is
derivable; auto-filling the rest invents architecture truth (§7). Already the
current behavior for the one derivable field; extending it to others is unsafe.

**Option B — separate Journey 2 authoring command/stage.**
A human-driven stage that prompts for the 13 fields and validates the result. This is
the *correct eventual home* for authoring, but it is a **new stage/UX**, not the
smallest slice, and not needed before there is demand to author a package.

**Option C — two-phase: machine evidence appendix + human authoring.**
Emit a non-authoritative `evidence` block (HLD anchors+roles from
`build_reference_map`, open questions from `collect_open_questions`, selected cards
from `engineering_selection`, a `slice_test_policy` pointer, the lens checklist) to
*assist* a human author, who then fills the 14 fields.
**Named defect (why not now):** every input it would copy
(`hld_reference_map.json`, open questions, selected cards) **already exists in the
package** — the appendix is a *second copy of source-of-truth data* with drift risk
(`CH:SO` / `OM:UE`), and it fills **zero of the 14 fields**, so it does not advance
the authoring path. No consumer needs it yet → speculative. Keep as a *future*
consideration, not this slice.

## 9b. The recommended *no-build* shape (what to do instead)

Do nothing to the code now. The emitted artifact is already honest: derivable field
grounded, the rest empty, verdict ACTION, advisory, ungated. When authoring is
actually needed, prefer **Option B** (human authoring stage) over Option C; never
Option A for the reasoning fields.

## 10. Recommendation

**DO_NOT_PATCH.** No safe automated authoring path exists for the 13 non-derivable
fields; the one derivable field is already emitted. Patching to derive more would
invent architecture truth. The smallest *safe* change is **no change** — the current
emit-empty-ACTION behavior is the correct state until a human (Option B) authors a
package.

## 11. Smallest safe next patch slice, if any

**None required now.** If/when a concrete package must be authored, the smallest safe
slice is **Option B**: a human-authoring stage that (a) loads the emitted slot, (b)
collects the 14 fields from the human with HLD anchor pointers shown as *evidence,
not values*, (c) runs `validate_architecture_package`, and (d) rewrites the artifact —
still advisory, still ungated. That slice is **human-input-driven**, not derivation.

## 12. Tests needed for that future (Option B) patch

- Authoring a complete set of 14 non-empty fields → `validate_architecture_package`
  PASS; rewritten artifact `advisory:True`, no longer ACTION.
- Any field left empty/missing → ACTION (validator already covers this; reassert at
  the stage boundary).
- `next_slice_packet` authored as descriptive data only — **no execution keys**
  (`command`/`argv`/`run`/`ready`/`action`/…); assert their absence.
- No `helper_selection` import or side effect; `helper_recommendation` remains
  advisory and value-agnostic to the verdict.
- Artifact stays in `AUTHORITATIVE_FILES`/manifest, excluded from
  `.specify/source/`, **absent from `REQUIRED_FILES`**, and **unreferenced by
  `gate_validator.py`** — `validate_source_package().ok()` unchanged by authoring.
- Evidence pointers (if any are shown to the human) are **read** from the existing
  package artifacts, never **copied** into `architecture_package.json` (no
  second source of truth).

## 13. What remains forbidden

No gate wiring; not in `REQUIRED_FILES`; no invented architecture truth; no
assumption-to-fact conversion; no helper selection; no `NextActionPacket`; no
`READY`; no execution channel; no autonomy; no new helpers; no CI; no
SourceBinding/governance change; no target mutation beyond the package artifact a
future human-authoring stage rewrites.

## 14. Gating

**Remain deferred.** The reason is exactly the §10 finding: there is no authoring
path, so the artifact is **ACTION by default**. Wiring an ACTION-by-default artifact
into `SOURCE_PACKAGE_APPROVAL_GATE` (or `REQUIRED_FILES`) would block **every**
promotion until a human authors all 14 fields — a governance change with whole-flow
blast radius. Gate only **after** Option B exists and packages can reach PASS.

## 15. RunSkeptic on this report and recommendation

- **Source:** `saffih/skeptic/skeptic.md` @
  `183acd39cc51a8ada33bcf7506d506aa528fbca7` (confirmed identical to that repo's
  origin/main; current).
- **Permission mode:** read-only (report only; no code touched).
- **Disconfirming case (PO):** *"`helper_recommendation` is derivable — doesn't that
  generalize?"* **No.** It is derived from `helper_registry` (capability metadata),
  **not** from HLD architecture content; `build_reference_map` proves the HLD yields
  faithful *section metadata* (role/risk/status), never *architecture intent / SoT /
  ownership*. The one derivable field is derivable for a reason that does not extend
  to the reasoning fields. This makes **DO_NOT_PATCH** falsifiable: show a 2nd field
  fillable from HLD evidence without judgment, and the recommendation changes.
- **CH (inversion):** worst outcome of acting = auto-deriving SoT/intent →
  manufactured truth, diverging sources, decorative upstream gates. DO_NOT_PATCH
  avoids it; the cost of *not* acting is only that authoring stays manual, which is
  correct today.
- **OM (parsimony):** the evidence appendix (Option C) is unnecessary structure
  (duplicate data, fills zero fields) — correctly *not* recommended.
- **FE (mechanism):** classification is mechanism-backed — each bucket cites a source
  function (`build_reference_map`, `build_helper_recommendations`, `DEFAULT_SLICES`)
  or a contract clause (§8 / §5).
- **KT:** the rule "machine fills only what it can ground faithfully; humans own
  architecture truth" universalizes across all 14 fields and future helpers.
- **SH:** automate-vs-don't-invent resolved with a dominant default (don't fill
  reasoning fields) and the one narrow exception (`helper_recommendation`,
  registry-grounded). No fake middle (the appendix would be one).
- **Result: PASS.**
- **Risks / unresolved questions:**
  1. Whether the eventual authoring UX is Option B vs C is a product call, not
     resolved here (recommendation: B).
  2. Semantic fidelity of any human-authored field is not machine-checkable (the
     validator proves structure only — `JOURNEY2_ARCHITECTURE_PACKAGE_CONTRACT.md` §8);
     unchanged by this report.
  3. If a future HLD schema adds structured SoT/ownership metadata, fields 3–4 could
     move toward DERIVABLE — re-evaluate then.

---

*This report is analysis only. No code behavior changed; no product file other than
this report was added or modified.*
