# Journey 2 — Architecture Package Contract (v0)

**Status:** product/architecture contract. This is the design-reasoning contract
for Journey 2 of the three-journey model (`docs/THREE_JOURNEYS.md`). It defines
the **architecture package** — the architecture wisdom and slice design Journey 2
produces — and the deterministic shape a package must satisfy.

It is validated by a pure helper, `hldspec/journey2_architecture_package.py`
(`validate_architecture_package`). That validator only validates a dict; it does
not read the filesystem, mutate anything, run a helper, or change helper
selection.

> **Now emitted as an advisory artifact.** The package builder
> (`hldspec/hld_source_package.py::build_source_package_content`) emits the typed
> slot as `architecture_package.json` via
> `journey2_architecture_package.build_architecture_package`. Mirroring
> `helper_recommendations.json`: it is hashed in the manifest (drift detectable),
> **excluded from `REQUIRED_FILES`** (advisory — packages stay valid without it)
> and **from the `.specify` mirror** (design reasoning, not SpecKit runner
> content), and wired into **no gate**. The emitter grounds only
> `helper_recommendation` (registry-derived, injected) and leaves the human-owned
> architecture-reasoning fields **empty**, so the artifact honestly validates
> **ACTION** until authored — it invents no architecture truth and promotes
> nothing.

> **Relationship to the existing Journey 2 docs.** This doc is **complementary**,
> not a replacement.
> - `docs/JOURNEY2_PACKAGE_CONTRACT.md` is the *compiler/packager mechanics*
>   contract: the already-implemented **target package** (anchors, manifest, spec
>   input, constitution proposal) under `target/.hldspec/source_package/`.
> - `docs/JOURNEY2_INQUIRY_LEDGER_CONTRACT.md` tracks open inquiries/gaps.
> - **This doc** is the *architecture-design lens*: the wisdom, contracts/seams,
>   expert-lens reasoning, and slice roadmap that *feed* and *organize* that
>   package. It bridges to the existing `engineering_guidelines.md` (architecture
>   constraints) and `implementation_slices.json` (slice set); it does not
>   introduce a competing slicer.

---

## 1. What Journey 2 is, in one line

> Journey 2 = SDD-ready HLD → **Architecture Package + Slice Roadmap +
> next_slice_packet + Helper Recommendation.**

### Purpose

- apply software architecture wisdom
- apply AI/software-engineering toolchain knowledge
- design for brownfield reality
- avoid brittle MVP traps
- avoid premature optimization
- create contracts/seams before behavior
- slice work into reviewable, testable, architecture-preserving chunks

### What "architecture wisdom" means here (and what it does *not*)

Journey 2 **organizes and makes explicit** the architecture that the SDD-ready
HLD already grounds: it names the source-of-truth map, ownership boundaries,
contracts/seams, and brownfield constraints, and reasons about them through
expert lenses. It **does not invent** architecture the HLD and human did not
decide — that prohibition from `JOURNEY2_PACKAGE_CONTRACT.md` §8 and
`THREE_JOURNEYS.md` §3 still holds. The architecture package is the *design
reasoning* over HLD-grounded material, not a license to author new product or
architecture truth.

---

## 2. Required architecture package sections

A v0 architecture package is a dict with these 14 required top-level fields
(`REQUIRED_ARCHITECTURE_PACKAGE_FIELDS`). Each must be present **and non-empty**:

| # | Field | Role |
|---|---|---|
| 1 | `product_goal_summary` | What the product/feature is for, in product terms. |
| 2 | `architecture_intent` | The intended architecture shape and why. |
| 3 | `source_of_truth_map` | Where each piece of truth lives; no split ownership. |
| 4 | `ownership_boundaries` | Which component/module owns which responsibility. |
| 5 | `contracts_and_seams` | The interfaces/seams to establish **before** behavior. |
| 6 | `brownfield_constraints` | Existing-system realities the design must respect. |
| 7 | `expert_lenses_applied` | Findings from the built-in expert lenses (§4). |
| 8 | `domain_assumptions` | Stated domain assumptions, so they can be challenged. |
| 9 | `slice_roadmap` | The ordered set of reviewable slices (§5). |
| 10 | `next_slice_packet` | A **descriptive** record of the next slice to do (§3). |
| 11 | `test_strategy` | How correctness/evidence is established across slices. |
| 12 | `forbidden_shortcuts` | Traps explicitly ruled out (brittle MVP, premature opt). |
| 13 | `growth_and_change_notes` | How the design absorbs growth without premature opt. |
| 14 | `helper_recommendation` | Advisory helper fit (§6) — a field, not a decision. |

A missing or empty required field is an **ACTION** (see §7).

---

## 3. `next_slice_packet` is data, not a channel

`next_slice_packet` is a **descriptive design field**: it records *which slice is
next and why*, as data, so a reader knows where the roadmap points. It is **not**:

- a `NextActionPacket` / `READY` execution prompt,
- an execution channel, a mutation channel, or autonomous execution.

This contract deliberately does **not** implement NextActionPacket / READY (see
Scope, §9). The naming similarity is intentional but the semantics differ: a
`next_slice_packet` describes; a NextActionPacket would *drive*. v0 only
describes.

---

## 4. Built-in v0 expert lenses

The canonical lens vocabulary (`BUILTIN_EXPERT_LENSES`). A package records its
lens findings under `expert_lenses_applied`; v0 validation requires that section
to be non-empty (it does not police *which* lenses appear):

- `software_architecture` — structure, coupling, cohesion, layering.
- `brownfield_integration` — fit with the existing system; no greenfield fantasy.
- `contracts_and_seams` — interfaces/seams before behavior; testable boundaries.
- `ai_agent_toolchain_safety` — safe use of AI/agent toolchains; bounded authority.
- `test_and_evidence` — what proves each slice correct; evidence over assertion.
- `git_worktree_pr_lifecycle` — branch/worktree/PR hygiene; reviewable units.
- `slice_quality` — each slice is reviewable, testable, architecture-preserving.

---

## 5. Slice quality requirements

Each slice in `slice_roadmap` must carry these 12 fields
(`REQUIRED_SLICE_FIELDS`), each present and non-empty:

- `id` — stable slice identifier.
- `name` — short human name.
- `purpose` — why this slice exists.
- `layer` — which architecture layer it touches.
- `allowed_changes` — what it may change.
- `forbidden_changes` — what it must not change.
- `expected_files_or_areas` — where it is expected to touch.
- `required_tests` — the tests that must pass for it.
- `dependency_ids` — slice ids it depends on. Must be **present**, but may be an
  empty list for a root slice with no dependencies.
- `risk_level` — assessed risk.
- `rollback_story` — how to undo it safely.
- `architecture_value` — what architecture property it establishes/preserves.

### Bad slice examples that must fail

The validator catches these deterministically:

- a slice **named/described** as `"implement the whole feature"`,
  `"refactor everything"`, `"add automation"`, or `"fix architecture"`
  (mega-slice phrasing → `slice_findings`);
- a **slice without tests** (`required_tests` missing/empty);
- a **slice without a rollback story** (`rollback_story` missing/empty).

Partially structural / otherwise human-reviewed:

- a **slice that mutates product code before a contract/seam exists** — v0 catches
  the structural part (the package must have non-empty `contracts_and_seams`, else
  ACTION), but whether a *specific* slice mutates before its seam is a
  human/RunSkeptic judgment, not a machine check in v0. The doc does not claim
  the validator catches the semantic case.

---

## 6. Helper recommendation — a field, not a decision

`helper_recommendation` is a required **advisory** field. It records which helper
is recommended for this package and why. It mirrors the already-emitted
`source_package/helper_recommendations.json`
(`hldspec/hld_source_package.py::build_helper_recommendations`, derived from
`hldspec/helper_registry.py`).

The validator treats it as opaque: it checks only that the field is present and
non-empty. The recommendation's **value never affects the verdict**, and this
module does **not** import or call `helper_selection`. Helper-selection semantics
are unchanged by this contract.

---

## 7. Validation states — PASS / ACTION

`validate_architecture_package(package)` returns:

```python
{
    "status": "PASS" | "ACTION",
    "missing_fields": [...],   # absent or empty required top-level fields
    "slice_findings": [...],   # per-slice issues (missing field / too broad)
    "notes": [...],            # human-readable summary lines
}
```

| Condition | Result |
|---|---|
| Missing/empty required package field | ACTION |
| Empty `slice_roadmap` | ACTION (it is a required, non-empty field) |
| Missing `next_slice_packet` | ACTION |
| Missing required slice field | ACTION (per-slice finding) |
| Slice too broad by obvious phrase | ACTION (per-slice finding) |
| No expert lenses applied | ACTION |
| No contracts/seams | ACTION |
| No brownfield constraints | ACTION |
| No forbidden shortcuts | ACTION |
| Structurally complete package | **PASS** |

There is no **BLOCKED** state: structural completeness is repairable, so this v0
gate is PASS/ACTION only. BLOCKED-class judgments (is this the *right*
architecture/decomposition?) remain human/RunSkeptic review, consistent with
`JOURNEY2_PACKAGE_CONTRACT.md` §9 and §14.

---

## 8. What this validator is honest about

- It proves **structural completeness**, not architectural correctness. A package
  can be structurally complete and still be a *bad* design — that is what the
  expert lenses, human review, and RunSkeptic are for.
- Mega-slice detection is phrase-based: it catches blatant breadth, not every
  vague slice.
- It is deterministic and AI-free by design.

---

## 9. Scope boundaries

This contract intentionally does **not** implement:

- SourceBinding
- ISG Governance
- NextActionPacket / READY (`next_slice_packet` is descriptive data — see §3)
- an execution channel
- a mutation channel
- autonomous execution
- new helpers
- helper-selection semantic changes
- SpecKit execution
- product-repo Git mutation
- a broad refactor of existing runtime/driver code

It adds this doc, the validation + advisory-emitter module
(`journey2_architecture_package.py`), the `architecture_package.json` emission
wiring in the package builder, and their tests. The emitter writes only the
advisory artifact into the existing source-package container; it adds no
execution channel, no mutation channel, and no helper-selection change.
