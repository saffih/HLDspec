# Journey 2 — Target Package Contract

**Status:** product contract. This is the testable gate for Journey 2 of the
three-journey model (`docs/THREE_JOURNEYS.md`). It defines the **target package**
Journey 2 produces and when that package may pass to Journey 3.

Like the Journey 1 contract, this documents and hardens **already-implemented**
mechanics. The package schema, validation, and gate live in
`hldspec/hld_source_package.py`, `hldspec/single_spec_input.py`,
`hldspec/spec_bundles.py`, and `hldspec/gate_validator.py`; this doc is their
binding contract, not a new mechanism.

> Naming: the three-journey framing calls the output a **target package**. The
> repo implements it as the **source package** under
> `target/.hldspec/source_package/`. This doc treats *target package* =
> *source package* and uses the existing file names (see §13).

---

## 1. Purpose

Compile an SDD-ready HLD into a structured, evidence-anchored **target package**
that Journey 3 can deliver into a target repo and operate with a selected helper.

Journey 2 is a **compiler / packager**, not an authoring assistant. It does not
improve the HLD — that was Journey 1. It does not deliver or run anything — that
is Journey 3.

## 2. Input

The **SDD-ready HLD** from Journey 1: the working HLD at verdict `HLD_READY`, or
`HLD_READY_WITH_ACTIONS` with human-accepted risks
(see `docs/JOURNEY1_SDD_READY_GATE.md`).

Journey 2 must **refuse** input that is `HLD_BLOCKED`. It never compiles around a
gate Journey 1 did not pass.

## 3. Output — the target package

The package lives at `target/.hldspec/source_package/`. Its authoritative files
(`hld_source_package.py::AUTHORITATIVE_FILES`):

| File | Role |
|---|---|
| `HLD.md` | Working HLD copy (package-local source truth). |
| `HLD.marked.md` | Anchored HLD: stable `<!-- ANCHOR: HLD-NNN -->` markers. |
| `hld_reference_map.json` | anchor → heading/title/role/risk/status/lines/sha256. |
| `speckit_single_spec_input.md` | One spec input; every requirement cites a `(HLD-NNN)` anchor. |
| `engineering_guidelines.md` | Architecture constraints, engineering tools, quality gates. |
| `implementation_slicing_policy.md` | How work is sliced (meaning, not line count). |
| `implementation_slices.json` | The slice set with scope/tests per slice. |
| `slice_test_policy.md` | Test expectations per slice. |
| `speckit_slice_execution_prompt.md` | Helper execution prompt for a slice. |
| `speckit_runbook.md`, `runner_prompt.md`, `consultant_prompt.md`, `human_review_package.md` | Operating/handoff material. |
| `anchor_coverage_schema.json` | Schema for anchor coverage checks. |
| `constitution.proposed.md` | Constitution material — **proposal only** (see §6). |
| `source_package.json` | Package metadata + binding fields (target path, SHAs). |
| `source_manifest.json` | File manifest with per-file SHA256. |

Plus the layered ordering artifacts when a multi-feature path is approved:
**feature dependency graph** + **SpecKit invocation queue**, both derived from one
`ordered_features` list (parity invariant — they must never diverge).

## 4. Boundaries

Journey 2:
- compiles the SDD-ready HLD into the package above;
- authors `constitution.proposed.md` as a *proposal*, never the applied constitution;
- validates anchor integrity and manifest before promotion.

Journey 2 does not: improve/repair the HLD, invent product truth, init SpecKit,
select or install a helper, deliver into the target repo, or run any phase. Those
are Journey 1 (upstream) and Journey 3 (downstream) boundaries.

---

## 5. Sub-schemas

### 5.1 Feature schema (`spec_bundles.py`)

Each feature/bundle carries:
- `feature_id` (from `feature_id` / `spec_id` / `planned_spec_id` / `id`),
- `source_hld_sections` — the HLD evidence it compiles from,
- `dependencies` — upstream feature_ids,
- bundle `id`, `name`, and a `reason` for the grouping.

Feature boundaries come from HLD groups → spec package map → bundles, grouped by
**meaning** (source of truth, architecture, interface/data ownership, dependency
order, testability) — never by line count.

### 5.2 Spec-input schema (`single_spec_input.py`)

`speckit_single_spec_input.md` is **one** input for one coherent HLD. Every claim
under `## Requirements` must cite a known `(HLD-NNN)` anchor. An uncited claim is
flagged (`claim cites unknown anchor`) and fails the build.

### 5.3 Constitution-material schema

`constitution.proposed.md` is authored in the package as a **proposal**. It is
applied to `.specify/memory/constitution.md` only at `CONSTITUTION_APPROVAL_GATE`,
where SpecKit owns the applied constitution. Augmented `CONTRACT-*` / `DATA-*`
rules must survive regeneration (existing invariant).

### 5.4 Helper recommendations — contracted, not yet emitted

The three-journey framing says Journey 2 should produce **helper recommendations**
(which helper(s) suit this package: `speckit`, `claude-code`, `codex`, `devin`,
`manual`). **No code emits this today** — it appears only in `THREE_JOURNEYS.md`.

Until a `helper_recommendations` field is added to `source_package.json`, Journey 3
defaults to `helper: speckit` (the only implemented helper). This is a known gap
(§14), stated honestly rather than implied as working.

---

## 6. Validation rules

Machine-checkable, from existing code:
- **Anchor integrity** — every spec-input requirement cites a known anchor;
  duplicate/mismatched anchors fail (`hld_marking.anchor_integrity_errors`,
  `single_spec_input.py`).
- **Manifest integrity** — `source_manifest.json` SHA256 per file; the package
  validates via `validate_source_package(...).ok()`.
- **Binding** — `source_package.json` binds the package to its target path and
  source SHAs so drift is detectable.
- **Parity** — feature dependency graph and invocation queue derive from one
  `ordered_features`; divergence is `CONFLICT: workflow source-of-truth conflict`.

## 7. What must be evidence-based

- Every requirement in the spec input cites an `HLD-NNN` anchor.
- Every feature's `source_hld_sections` references real HLD sections.
- Constitution `CONTRACT-*`/`DATA-*` rules trace to HLD contracts/data ownership.

## 8. What must not be invented

- Requirements, features, or boundaries with no HLD anchor.
- Constitution rules not grounded in the HLD.
- Source-of-truth or data-ownership decisions the HLD/human did not make.
- Helper *choices* presented as package truth (recommendations are advisory).

A well-formed but empty/stub HLD still builds a **well-formed** package
(`ok=True`, 0 anchors) — well-formed is *not* approval-ready; the gate blocks
promotion.

---

## 9. Gate states — PASS / ACTION / BLOCKED

Bound to `SOURCE_PACKAGE_APPROVAL_GATE`
(`gate_validator.py`: requires receipt, source refs, RunSkeptic PASS, Consultant
PASS, human approval; blockers also from `unsupported_claims`, `stale_anchors`,
`validation_ok`).

| Gate state | Meaning | Trigger |
|---|---|---|
| **PASS** | The package is complete, anchor-clean, evidence-based, and approved. Journey 3 may consume it. | `validation_ok`, no `unsupported_claims`, no `stale_anchors`, RunSkeptic PASS, Consultant PASS, human approval. |
| **ACTION** | Mostly complete, but specific fixable issues remain before Journey 3. | Uncited claims, stale anchors, missing source refs, manifest drift, or RunSkeptic ACTION — all repairable without a human-owned design decision. |
| **BLOCKED** | The package cannot be safely promoted. | RunSkeptic CONFLICT, Consultant BLOCK, graph/queue parity conflict, an unresolved human-owned decision, or input that was `HLD_BLOCKED`. |

**Promotion rule:** Journey 3 consumes only **PASS**. ACTION returns to Journey 2
for the fix. BLOCKED never promotes; if the root cause is upstream, it returns to
**Journey 1**, not patched here.

## 10. What Journey 2 must not do

- Must not author the applied constitution (proposal only, applied at its gate).
- Must not write into `.specify/` as authoritative (only the generated, banner-
  stamped mirror is allowed; authoritative files stay in `.hldspec/`).
- Must not invent un-anchored requirements/features/rules.
- Must not init SpecKit, select/install a helper, or deliver into the target repo.
- Must not promote a package built from an `HLD_BLOCKED` input.

## 11. What Journey 2 must not allow into Journey 3

Never hand downstream:
- a package with any uncited spec-input claim or stale anchor;
- a feature with empty/unreal `source_hld_sections`;
- diverging feature graph vs invocation queue;
- an unapplied human-owned decision (RunSkeptic CONFLICT / Consultant BLOCK);
- a constitution proposal whose `CONTRACT-*`/`DATA-*` rules were wiped by regen.

Journey 3 must never compensate for a package that should not have passed.

## 12. RunSkeptic questions for Journey 2

- **CH (inversion):** If this package ships, what is the worst thing Journey 3
  builds from it, and does anchor integrity + the gate bound it?
- **OM (parsimony):** Is each package file earning its place, or is the package
  carrying artifacts no helper consumes?
- **FE (mechanism):** Can a reader see *how* each requirement traces to the HLD
  (anchor map), not just that it "came from the HLD"?
- **PO (refutation):** Show a package this gate would block. Can an un-anchored
  claim pass silently? (It should fail the build.)
- **KT (universalizability):** Is the package shape safe for every SDD-ready HLD,
  including a single-feature one, without special-casing?
- **SH (tradeoff):** Single coherent spec input (default) vs meaningful layering
  — is the dominant default clear, with a narrow exception for independently
  valuable layers?

## 13. Vocabulary bridge

| Framing name | Existing repo artifact |
|---|---|
| target package | `target/.hldspec/source_package/` |
| spec input | `speckit_single_spec_input.md` |
| feature / feature brief | `spec_bundles.py` bundle (`feature_id`, `source_hld_sections`, `dependencies`) |
| architecture constraints / engineering tools / quality gates | `engineering_guidelines.md` |
| constitution material | `constitution.proposed.md` (+ `CONTRACT-*`/`DATA-*` augmentation) |
| package metadata / manifest | `source_package.json` / `source_manifest.json` |
| package gate | `SOURCE_PACKAGE_APPROVAL_GATE` (+ `CONSTITUTION_APPROVAL_GATE`) |
| helper recommendations | *not yet emitted* — see §5.4 / §14 |

## 14. Known limits (honest scope)

- **Helper recommendations are not produced.** Journey 3 currently defaults to
  `helper: speckit`. Adding `helper_recommendations` to `source_package.json` is
  the concrete Journey 2 ↔ Journey 3 seam to define in Prompt 3.
- Anchor integrity proves a requirement *cites* an anchor; it does not prove the
  requirement faithfully reflects that anchor's intent — semantic fidelity remains
  human/Consultant-reviewed at the gate.
- The layered feature graph/queue parity is enforced structurally; whether a given
  decomposition is the *right* set of boundaries is a human/RunSkeptic judgment,
  not a machine check.

## 15. Minimal test / validation strategy

**Automated (existing seams):**
- `single_spec_input.py` — uncited claim fails the build (anchor integrity).
- `hld_source_package.py::validate_source_package().ok()` — manifest/package shape.
- `spec_bundles.py` — graph/queue derive from one `ordered_features` (parity).
- `gate_validator.py` — `SOURCE_PACKAGE_APPROVAL_GATE` blocks without RunSkeptic
  PASS / Consultant PASS / human approval.

**Manual checklist** (per package):
1. Every spec-input requirement cites a real `HLD-NNN` anchor.
2. Every feature's `source_hld_sections` is non-empty and real.
3. Feature graph and invocation queue agree.
4. `constitution.proposed.md` keeps its `CONTRACT-*`/`DATA-*` rules.
5. No authoritative content written into `.specify/` (only the banner mirror).
6. Verdict matches: any un-anchored claim or parity conflict → not PASS.
