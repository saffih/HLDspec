# Journey 2 — SDD / Source-Package Readiness Gate Inventory

**Status:** inventory (discovery only). Maps what exists today for Journey 2
readiness enforcement, separates enforceable-now from defined-but-not-wired,
and identifies the smallest next implementation slice.

**Date:** 2026-06-30

---

## Q1. Where is readiness / PASS currently decided?

There is no single "Journey 2 readiness gate" today. Readiness enforcement is
split across several independent surfaces:

| Surface | Location | What it checks | Live? |
|---|---|---|---|
| **Source-package structural validation** | `hldspec/hld_source_package.py::validate_source_package` | Required files present + manifest hash integrity | **Yes** — called by `build_source_package_content` (line 525) and `journey3_driver.py` (line 85) |
| **Gate validator — SOURCE_PACKAGE_APPROVAL_GATE** | `hldspec/gate_validator.py::validate_gate` | Receipt present, source refs, RunSkeptic PASS, Consultant PASS, human approval, stale anchors, unsupported claims, validation_ok | **Yes** — called by `session_control.py` (line 774) during preflight |
| **SpecKit readiness dir-exists check** | `hldspec/speckit_readiness.py` (line 278) | `.hldspec/source_package/` directory exists | **Yes** — simple existence check, not content validation |
| **HLD readiness machine** | `hldspec/machines/hld_readiness.py::HldReadinessMachine` | Cross-examination of HLD items → verdict (HLD_READY / HLD_READY_WITH_ACTIONS / HLD_BLOCKED) | **Yes** — but this is Journey 1 (HLD→SDD-ready), not Journey 2 (SDD→package-complete) |

**The live PASS surface for Journey 2 is: `validate_source_package` (structural)
+ `validate_gate(SOURCE_PACKAGE_APPROVAL_GATE, ...)` (full gate with RunSkeptic /
Consultant / human approval).** Everything else is either Journey 1 or not yet wired.

---

## Q2. What artifacts exist today?

### Defined + tested (contracts module exists, unit tests pass)

| Artifact concept | Module | Test file | State |
|---|---|---|---|
| **HLD Coverage Ledger items** (item types, coverage statuses, risk levels) | `hldspec/journey2_hld_coverage_contracts.py` | `tests_v2/test_journey2_hld_coverage_contracts.py` | Contract + validation helpers only. Pure functions. **No producer, no pipeline caller.** |
| **HLD Requirement Inventory** (list of HLD items with stable IDs) | `hldspec/journey2_hld_coverage_contracts.py::validate_requirement_inventory` | `tests_v2/test_journey2_hld_coverage_contracts.py` | Validator only. **No producer.** |
| **SDD Completeness Report** | `hldspec/journey2_hld_coverage_contracts.py::build_completeness_report` | `tests_v2/test_journey2_hld_coverage_contracts.py` | Builder exists but **called only from tests**. Not wired into any gate or pipeline. |
| **SDD Section Coverage Map** (reverse: SDD→HLD) | `hldspec/journey2_hld_coverage_contracts.py::build_sdd_section_coverage_map` | `tests_v2/test_journey2_hld_coverage_contracts.py` | Pure function, tests-only caller. |
| **Context Safety Gap Ledger** (worker receipts, gap items, evidence map) | `hldspec/context_safety_gap_contracts.py` | `tests_v2/test_context_safety_gap_contracts.py` | Pure validation. Brownfield-decomposition flavor. **No pipeline caller outside tests.** |
| **Architecture Package** (14 required fields, slice roadmap) | `hldspec/journey2_architecture_package.py` | `tests_v2/test_journey2_architecture_package.py` | Emitted as advisory slot by `build_source_package_content`. Excluded from REQUIRED_FILES, mirror, and all gates. ACTION until authored. |
| **Source package manifest + metadata** | `hldspec/hld_source_package.py` | `tests_v2/test_source_package.py` | **Live** — written and validated during build + Journey 3 driver. |
| **Helper recommendations** | `hldspec/hld_source_package.py::build_helper_recommendations` | `tests_v2/test_source_package.py` | **Live** — emitted during build, manifest-hashed, excluded from mirror/required. |

### Source inventory

There is no standalone artifact named `source_inventory` today. The current
source inventory is distributed across live source-package artifacts:

| Inventory surface | Current state |
|---|---|
| `hld_reference_map.json` | **Live** — HLD anchors, heading/title, role/risk/status, line range, and hashes. |
| `source_manifest.json` / `source_package.json` | **Live** — package metadata, binding fields, and file hashes. |
| `speckit_single_spec_input.md` | **Live** — SDD input surface; requirements cite `(HLD-NNN)` anchors. |
| HLD Requirement Inventory | **Contract-only** — validator exists in `journey2_hld_coverage_contracts.py`, but no producer emits it from the source package yet. |

### Docs-only (contracted but no code)

| Artifact concept | Contract doc | Notes |
|---|---|---|
| **`inquiry_ledger.json`** | `docs/JOURNEY2_INQUIRY_LEDGER_CONTRACT.md` | Question lifecycle (OPEN/ESCALATED/ASSUMED/RESOLVED). Backlog P1-013, Slice B. |
| **`gap_register.json`** | `docs/JOURNEY2_INQUIRY_LEDGER_CONTRACT.md` | Gap severity (BLOCKER/WARNING/NOTE). Backlog P1-013, Slice B. |
| **Lens registry** | `docs/JOURNEY2_INQUIRY_LEDGER_CONTRACT.md` | Inquiry frames (DOMAIN/ARCHITECTURE/QUALITY/TOOL_HELPER). Backlog P1-013, Slice A. |
| **`open_questions.md`**, **`answered_assumptions.md`**, **`test_strategy.md`** | `docs/JOURNEY2_INQUIRY_LEDGER_CONTRACT.md` | Advisory views rendered from ledger. Backlog P1-013, Slice D. |
| **Research Ledger** | `docs/JOURNEY2_SDD_COMPLETENESS_GATE.md` §4 | Research obligations tracking. No backlog slice yet. |

### Assumptions and conflicts

| Concept | Current state |
|---|---|
| **Assumptions** | Represented in docs-only inquiry artifacts (`answered_assumptions.md`) and contract fields such as coverage-ledger `assumption`; no live producer or gate wiring. |
| **Conflicts** | Enforceable only where already represented by live fields (`RunSkeptic CONFLICT`, source-package split-brain, spec-build quality conflicts). Gap-ledger `CONFLICT` is validated in tests but not wired. |

### RunSkeptic receipt

Not a standalone artifact. RunSkeptic status is a **string field** (`runskeptic_status`)
carried inside `GateContext` (`gate_validator.py`) and
`speckit_prework_quality_review.json`. There is no separate `skeptic_receipt.json`
artifact today.

---

## Q3. Which readiness blockers are already enforceable from existing fields?

These block **today** via live pipeline callers:

| Blocker | Enforcer | How |
|---|---|---|
| Required source-package files missing | `validate_source_package` → `SourcePackageValidation.missing` | `journey3_driver.py` refuses invalid package |
| Manifest hash mismatch (file drift) | `validate_source_package` → `SourcePackageValidation.hash_mismatches` | Same |
| Missing Context Receipt | `validate_gate(SOURCE_PACKAGE_APPROVAL_GATE)` | `session_control.py` preflight |
| Missing source refs/anchors | `validate_gate(SOURCE_PACKAGE_APPROVAL_GATE)` | `session_control.py` preflight |
| RunSkeptic ACTION or CONFLICT | `validate_gate(SOURCE_PACKAGE_APPROVAL_GATE)` | `session_control.py` preflight |
| Missing RunSkeptic PASS (when required) | `validate_gate(SOURCE_PACKAGE_APPROVAL_GATE)` | `session_control.py` preflight |
| Consultant BLOCK | `validate_gate(SOURCE_PACKAGE_APPROVAL_GATE)` | `session_control.py` preflight |
| Missing Consultant PASS (when required) | `validate_gate(SOURCE_PACKAGE_APPROVAL_GATE)` | `session_control.py` preflight |
| Missing human approval | `validate_gate(SOURCE_PACKAGE_APPROVAL_GATE)` | `session_control.py` preflight |
| Stale anchors | `validate_gate(SOURCE_PACKAGE_APPROVAL_GATE)` | `session_control.py` preflight |
| Unsupported claims in spec input | `validate_gate(SOURCE_PACKAGE_APPROVAL_GATE)` | `session_control.py` preflight |
| Failed validation | `validate_gate(SOURCE_PACKAGE_APPROVAL_GATE)` | `session_control.py` preflight |
| Source-package split-brain (external mode) | `hld_source_package.py::source_package_split_brain` | Detects conflicting packages |

---

## Q4. Which blockers are only documented / defined but not enforceable yet?

| Blocker | Where defined | Why not enforceable |
|---|---|---|
| **HLD item NOT_COVERED** | `journey2_hld_coverage_contracts.py::BLOCKING_STATUSES` | No producer populates the coverage ledger. `build_completeness_report` is called only from tests. Not wired into `SOURCE_PACKAGE_APPROVAL_GATE`. |
| **NEEDS_CLARIFICATION without inquiry entry** | `JOURNEY2_SDD_COMPLETENESS_GATE.md` §6 | Inquiry ledger does not exist in code (P1-013). |
| **RESEARCH_REQUIRED without evidence** | `JOURNEY2_SDD_COMPLETENESS_GATE.md` §6–§7 | Research ledger does not exist. |
| **BLOCKED_BY_PRODUCT_DECISION unresolved** | `journey2_hld_coverage_contracts.py` | Defined as status; no producer or gate wiring. |
| **SDD sections with no HLD grounding** (UNLINKED) | `journey2_hld_coverage_contracts.py::unlinked_sdd_sections` | Pure function, no caller. |
| **Architecture package ACTION** (empty fields) | `journey2_architecture_package.py` | Deliberately excluded from all gates — advisory only. |
| **ESCALATED inquiry question unresolved** | `JOURNEY2_INQUIRY_LEDGER_CONTRACT.md` §3 | Inquiry ledger not implemented (P1-013 Slice B). |
| **BLOCKER gap open** | `JOURNEY2_INQUIRY_LEDGER_CONTRACT.md` §4 | Gap register not implemented (P1-013 Slice B). |
| **Brownfield gap ledger BLOCKING/CONFLICT** | `context_safety_gap_contracts.py` | Validation helpers exist; no pipeline caller outside tests. |
| **Worker receipt compactness exceeded** | `context_safety_gap_contracts.py` | Validated in `gap_ledger_blockers`; no live caller. |
| **Missing worker decomposition** | `context_safety_gap_contracts.py` | Same — tests only. |

---

## Q5. Smallest next implementation slice

The coverage ledger *contracts* are done (`journey2_hld_coverage_contracts.py`
has validators, `build_completeness_report`, all 14 item types and 6 statuses,
with full test coverage). The `JOURNEY2_SDD_COMPLETENESS_GATE.md` §12 item 1
("add coverage ledger contracts") is **already complete**.

**Smallest next implementation slice:** Produce a coverage ledger from the HLD
reference map during source-package build.

Concretely:

1. Extend `build_source_package_content` to emit an initial coverage ledger from
   `hld_reference_map.json`.
2. For each HLD anchor, create one requirement-inventory / coverage-ledger entry.
3. Mark entries conservatively:
   - `COVERED_IN_SDD` only when the generated SDD/spec input cites the anchor.
   - `NOT_COVERED` otherwise.
4. Register the emitted artifact in source-package manifest/hash validation.
5. Tests: source package with two anchors, one cited and one uncited, produces a
   deterministic coverage ledger without changing gate behavior yet.

> `feat(journey2): produce coverage ledger from HLD reference map during source-package build`

This generates an initial coverage ledger where every HLD anchor gets an entry
with status `NOT_COVERED` (or `COVERED_IN_SDD` if the spec input cites it).

The follow-on slice can then wire `build_completeness_report` into
`SOURCE_PACKAGE_APPROVAL_GATE` as an ACTION/BLOCKED enrichment. Without the
producer slice first, gate wiring has no live data to check.

---

## Existing tests found

| Test file | What it covers |
|---|---|
| `tests_v2/test_journey2_hld_coverage_contracts.py` | All coverage ledger validation: item types, statuses, status-specific constraints, inventory validation, duplicate IDs, completeness report, SDD section coverage map, unlinked sections, authority boundary |
| `tests_v2/test_journey2_architecture_package.py` | Architecture package validation: 14 required fields, slice validation, mega-slice detection, build function, advisory notes |
| `tests_v2/test_context_safety_gap_contracts.py` | Gap ledger: gap types/statuses, worker receipt compactness, evidence map, RunSkeptic reconciliation, authority grants, BLOCKING/CONFLICT/ASSUMED_FOR_NOW rules |
| `tests_v2/test_gate_validator.py` | Gate validation: all gate requirements, RunSkeptic/Consultant status handling, blocker accumulation |
| `tests_v2/test_source_package.py` | Source package: build, validate, manifest, mirror, binding, helper recommendations |

---

## Cross-references

- `docs/JOURNEY2_SDD_COMPLETENESS_GATE.md` — product direction (this inventory's parent)
- `docs/JOURNEY2_PACKAGE_CONTRACT.md` — structural package contract
- `docs/JOURNEY2_INQUIRY_LEDGER_CONTRACT.md` — epistemic state contract (P1-013)
- `docs/JOURNEY2_ARCHITECTURE_PACKAGE_CONTRACT.md` — architecture-design lens
- `docs/HLDSPEC_DEVELOPMENT_BACKLOG.md` — P1-013 slices A–D
