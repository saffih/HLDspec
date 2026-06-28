# Journey 2 — SDD Completeness Gate (Product Direction)

**Status:** product direction (docs-only). This doc defines a future Journey 2
capability — the **HLD Coverage Ledger / SDD Completeness Gate** — that enforces
traceability from every HLD item into the SDD/package. It does not implement the
gate, generate SDDs, invoke SpecKit, or mutate target repos.

> **Relationship to existing Journey 2 docs.** This doc is **complementary**,
> not a replacement.
> - `docs/JOURNEY2_PACKAGE_CONTRACT.md` is the *compiler/packager mechanics*
>   contract: the target package schema, anchor-integrity validation,
>   evidence-based rules, and `SOURCE_PACKAGE_APPROVAL_GATE` (PASS/ACTION/BLOCKED).
>   That gate validates **structural** package completeness — required files
>   present, anchors intact, manifest consistent.
> - `docs/JOURNEY2_ARCHITECTURE_PACKAGE_CONTRACT.md` is the *architecture-design
>   lens*: 14 required fields, slice roadmap, expert-lens reasoning. Advisory —
>   validates ACTION until authored.
> - `docs/JOURNEY2_INQUIRY_LEDGER_CONTRACT.md` tracks *epistemic state*: open
>   questions (`inquiry_ledger.json`), gaps (`gap_register.json`), lens registry,
>   and gate integration. It owns the question lifecycle
>   (OPEN/ESCALATED/ASSUMED/RESOLVED/DEFERRED) and gap severity
>   (BLOCKER/WARNING/NOTE).
> - **This doc** addresses a different gap: **HLD-item→SDD-section coverage
>   traceability**. The existing package gate checks "are the required files
>   present and internally consistent?" but not "does the package account for
>   every requirement, constraint, and decision in the HLD?" That is the
>   dimension this capability adds. It reuses the inquiry ledger for
>   clarifications and the gap register for blockers — it does not duplicate them.

---

## 1. Problem

A generic prompt — "write a complete SDD from this HLD, cover everything,
research best practices, list gaps" — is an instruction, not an enforcement
mechanism. It depends on model compliance, not structural guarantees.

Observed failure modes:

- **Silent omission.** HLD sections with no obvious SDD counterpart (NFRs,
  operational constraints, security requirements, data ownership rules) are
  quietly dropped. No artifact records their absence.
- **Ambiguity absorption.** Unclear HLD content is silently resolved by the
  model instead of being flagged. The resolution is invisible and untracked.
- **Invented authority.** Research-shaped claims appear without sources.
  Technology choices are presented as settled when the HLD left them open.
- **Shallow treatment.** Components get API signatures but no error handling,
  observability, security, or data-ownership design. The SDD looks complete
  but is structurally hollow.
- **No traceability.** There is no map from HLD items to SDD sections. When
  the HLD changes, there is no way to know which SDD sections are affected.

"Do not skip anything" does not fix these. HLDspec must enforce coverage
through artifacts and gates, not through prompt wording.

HLDspec must support DTM-grade single-HLD/spec work: thorough, traceable,
slower if needed, but not shallow. Quality must not depend on model memory
or prompt compliance alone.

---

## 2. Scope and journey placement

This capability belongs to **Journey 2 — SDD / Package Preparation**.

| Journey | Role | Relationship to this capability |
|---|---|---|
| Journey 0 | Brownfield discovery / HLD gap-assessment | Discovers pre-HLD evidence. Not in scope. |
| Journey 1 | HLD Authoring / HLD Hardening | Hardens the HLD until SDD-ready. Produces the input this capability consumes. |
| **Journey 2** | **SDD / Package Preparation** | **Compiles HLD into package. This capability ensures the compilation is traceable and complete.** |
| Journey 3 | Target Delivery + Helper Runtime | Consumes the package. Not in scope. |

Journey 1 answers: *is the HLD clear enough to decompose?*
Journey 2 answers: *is the package complete, evidence-based, and traceable to
the HLD?*

The existing `SOURCE_PACKAGE_APPROVAL_GATE` validates structural package
completeness. This capability adds a **coverage dimension**: does the package
account for every HLD item? The completeness gate is a future sub-gate or
enrichment of the existing approval gate — not a free-floating parallel gate.

---

## 3. Required capability

**Name:** HLD Coverage Ledger / SDD Completeness Gate

**Purpose:** Every HLD section, requirement, component, workflow, constraint,
non-functional requirement, data/API/security/integration item, ambiguity,
and open question must be inventoried and tracked into the SDD/package.

The coverage ledger is the traceability matrix from HLD items to SDD/package
sections. The completeness gate blocks when coverage is incomplete or when
tracked items have unresolved statuses.

This is not a quality judgment of the SDD content — it is a coverage check:
*is everything accounted for, even if some items are explicitly deferred or
marked as needing clarification?*

---

## 4. Required artifacts

### New artifacts (genuinely new — no existing equivalent)

| Artifact | Purpose |
|---|---|
| **HldRequirementInventory** | Exhaustive enumeration of every requirement, constraint, decision, component, workflow, NFR, data/API/security item, and open question in the HLD. The input to coverage tracking. Each item gets a stable ID, source section, source text, and type classification. |
| **HldCoverageLedger** | The traceability matrix. Maps every inventory item to its SDD/package treatment: which SDD section covers it, what design decision was made, what status it has. The centerpiece of this capability. |
| **SddSectionCoverageMap** | The reverse view: for each SDD/package section, which HLD items it addresses. Enables completeness review from the SDD side — surfaces SDD sections with no HLD grounding (potential invention) and HLD items with no SDD section (potential gaps). |
| **ResearchLedger** | Tracks research obligations: items requiring investigation (technology choices, best practices, security patterns, scalability approaches). Each entry records the question, evidence found, sources, and whether the research is sufficient for the design decision. |
| **SddCompletenessReport** | The final gate artifact. Summarizes coverage status, lists uncovered items, clarification blockers, research blockers, product decision blockers, assumptions, and recommended fixes. |

### Existing artifacts reused (not duplicated)

| Existing artifact | Owner doc | How this capability uses it |
|---|---|---|
| `inquiry_ledger.json` | `JOURNEY2_INQUIRY_LEDGER_CONTRACT.md` | Clarifications and open questions are tracked here. The coverage ledger references inquiry-ledger entries by ID for items with status `NEEDS_CLARIFICATION`. This capability does not create a parallel clarification tracker. |
| `gap_register.json` | `JOURNEY2_INQUIRY_LEDGER_CONTRACT.md` | Gaps with severity (BLOCKER/WARNING/NOTE) are tracked here. The coverage ledger references gap-register entries for items with blocking gaps. This capability does not create a parallel gap tracker. |
| `hld_reference_map.json` | `JOURNEY2_PACKAGE_CONTRACT.md` | The anchor→heading/role/risk map. The requirement inventory aligns with this — each inventory item cites the relevant HLD anchor(s). |

---

## 5. Coverage ledger fields

Each row in the HLD Coverage Ledger tracks one HLD item:

| Field | Description |
|---|---|
| `HLD_ITEM_ID` | Stable identifier (aligned with HLD anchor where possible). |
| `SOURCE_SECTION` | HLD section the item comes from. |
| `SOURCE_TEXT` | The requirement/constraint/decision text from the HLD. |
| `ITEM_TYPE` | Classification: `REQUIREMENT`, `CONSTRAINT`, `COMPONENT`, `WORKFLOW`, `NFR`, `DATA_ITEM`, `API_CONTRACT`, `SECURITY_ITEM`, `INTEGRATION_POINT`, `DEPLOYMENT_ITEM`, `OPERATIONAL_ITEM`, `AMBIGUITY`, `OPEN_QUESTION`, `PRODUCT_DECISION`. |
| `STATUS` | Coverage status (see below). |
| `SDD_SECTION` | Which SDD/package section(s) address this item. Empty if not yet covered. |
| `DESIGN_DECISION` | The design decision made for this item, if any. |
| `RESEARCH_REQUIRED` | Whether research is needed. If yes, links to the research ledger entry. |
| `RESEARCH_EVIDENCE` | Summary of research findings, with source references. |
| `CLARIFICATION_REQUIRED` | Whether clarification is needed. If yes, links to the inquiry ledger entry. |
| `ASSUMPTION` | Any assumption made about this item. Must be explicit, never silent. |
| `ACCEPTANCE_CRITERIA` | Testable acceptance criteria derived from this HLD item. |
| `TEST_MAPPING` | Which test(s) verify this item's implementation. |
| `RISK` | Risk level: `HIGH`, `MEDIUM`, `LOW`. Drives depth of treatment. |

### Coverage statuses

| Status | Meaning |
|---|---|
| `COVERED_IN_SDD` | Item has a corresponding SDD section with a design decision. |
| `NEEDS_CLARIFICATION` | Item is ambiguous or incomplete. Linked to `inquiry_ledger.json` entry. Must not be silently resolved. |
| `BLOCKED_BY_PRODUCT_DECISION` | A product decision is needed that the system cannot make. Escalated. |
| `RESEARCH_REQUIRED` | Item needs investigation before a design decision can be made. Linked to research ledger entry. |
| `OUT_OF_SCOPE_BY_EXPLICIT_DECISION` | Explicitly excluded with rationale. Not silently dropped. |
| `NOT_COVERED` | Item has no SDD treatment and no explicit exclusion. **This is the blocking status.** |

---

## 6. Gate rules

The SDD Completeness Gate blocks (returns ACTION or BLOCKED, consistent with
the `SOURCE_PACKAGE_APPROVAL_GATE` vocabulary) when any of:

- Any HLD item has status `NOT_COVERED`.
- An ambiguity is hidden instead of tracked as `NEEDS_CLARIFICATION` with an
  `inquiry_ledger.json` entry.
- A product decision is needed but silently resolved by the model instead of
  escalated as `BLOCKED_BY_PRODUCT_DECISION`.
- `RESEARCH_REQUIRED` items have no research evidence and no explicit deferral
  rationale.
- Non-functional requirements lack design treatment (not just
  acknowledgment — actual design decisions about how they are met).
- Components lack relevant data/API/error-handling/security/observability
  treatment where the HLD implies they need it.
- Assumptions are not explicit in the `ASSUMPTION` field.
- `ACCEPTANCE_CRITERIA` or `TEST_MAPPING` is missing where the item type
  requires it (requirements, NFRs, workflows, API contracts).
- The `SddSectionCoverageMap` shows SDD sections with no HLD grounding
  (potential invented content — warns, does not block by default).

The gate is an enrichment of the existing `SOURCE_PACKAGE_APPROVAL_GATE`, not a
separate gate. A package that passes structural validation but fails coverage
validation is ACTION (fixable) or BLOCKED (requires upstream rework), consistent
with existing vocabulary.

---

## 7. Research policy

Research is required — not optional — for:

- Technology choices the HLD leaves open or underspecified.
- Best-practice questions (architecture patterns, security patterns, scaling
  strategies) where the design decision should be informed, not guessed.
- Security, scalability, reliability, and operational topics where current
  best practice matters.
- Data ownership, API design, integration patterns where conventions exist.
- Deployment and infrastructure topics where the target environment matters.

Research output rules:

- Research evidence must be attached to the relevant coverage ledger item
  and/or research ledger entry.
- Research must not become invented authority — it supports design decisions,
  it does not replace product decisions.
- If research findings may have changed since last gathered (e.g., library
  versions, API deprecations, security advisories), research must be
  refreshed before the gate can pass.
- "I researched this" without evidence is not research. The research ledger
  must record what was found, where, and whether it is sufficient.

---

## 8. Clarification policy

Missing or ambiguous HLD content must be flagged, not silently resolved.

- Flagged items are tracked in the existing `inquiry_ledger.json` (owned by
  `JOURNEY2_INQUIRY_LEDGER_CONTRACT.md`), not in a parallel system.
- The coverage ledger references the inquiry entry by ID and sets status to
  `NEEDS_CLARIFICATION`.
- The system may propose options for resolving ambiguity, but it must not
  silently choose unless the human explicitly allows it.
- If a proposed design is offered despite ambiguity, the assumption must be
  recorded in the `ASSUMPTION` field and the item must remain non-final
  (status stays `NEEDS_CLARIFICATION`) until the human accepts.
- Clarifications resolved by the human update both the inquiry ledger
  (RESOLVED) and the coverage ledger (status transitions to `COVERED_IN_SDD`
  or another terminal status).

---

## 9. Completeness report

The `SddCompletenessReport` is the final output of the gate. Before the
SDD/package can be approved, it must answer:

| Question | Expected answer for PASS |
|---|---|
| All HLD items inventoried? | Yes — count matches HLD content. |
| All items have a non-`NOT_COVERED` status? | Yes. |
| Uncovered items? | None. |
| `NEEDS_CLARIFICATION` items? | Zero, or all have accepted assumptions. |
| `RESEARCH_REQUIRED` items? | Zero, or all have sufficient evidence or explicit deferral. |
| `BLOCKED_BY_PRODUCT_DECISION` items? | Zero — all escalated and resolved. |
| Explicit assumptions? | Listed — none silent. |
| SDD sections with no HLD grounding? | Listed — reviewed for invented content. |
| Recommended fixes? | None blocking. |

---

## 10. Prior art and adopted control patterns

HLDspec is not inventing this discipline from scratch. The coverage ledger and
completeness gate borrow proven control ideas from requirements engineering,
architecture documentation, design review, and security analysis — adapted to
be lightweight, repo-native, typed, and testable.

| Pattern | Adopted as | Purpose |
|---|---|---|
| **Requirements traceability matrix** | `HldCoverageLedger` | Every HLD item maps to SDD coverage, decision, research/clarification status, and test/acceptance mapping. |
| **Architecture viewpoints / concern coverage** | `SddSectionCoverageMap` | Completeness is not only section count. Relevant design views must be covered: context, components, interfaces, data, state/lifecycle, security, observability, deployment, error handling, verification. |
| **Design rationale / ADR-style thinking** | `DESIGN_DECISION`, `ASSUMPTION`, `RESEARCH_EVIDENCE` fields in the ledger | Important design choices record context, options/tradeoffs, chosen decision, assumptions, and consequences — not just the conclusion. |
| **Formal inspection** | Completeness gate + gate rules (§6) | Detect defects before downstream implementation depends on the SDD. The gate is deterministic and structural, not a prose review. |
| **Threat-model-style skeptical taxonomy** | Compact defect classes (below) | Name the failure modes that make output *look* complete while silently dropping requirements, hiding assumptions, or failing to map design to verification. |
| **RunSkeptic** | Adversarial inspection layer | RunSkeptic attacks the coverage ledger and completeness report; it does not replace them. |

### Defect classes

These are the *failure modes* this capability is designed to catch. They are a
different axis from coverage statuses (§5) and gap severities
(BLOCKER/WARNING/NOTE in the inquiry ledger). Coverage statuses track *what
state an item is in*; defect classes name *what went wrong* when the output
looks complete but isn't:

| Class | Meaning |
|---|---|
| `MISSING` | HLD item has no SDD treatment and no explicit exclusion. |
| `VAGUE` | SDD section exists but lacks actionable design decisions. |
| `GUESS` | Design decision made without evidence or research. |
| `UNLINKED` | SDD section has no HLD grounding (potential invention). |
| `UNRESEARCHED` | Research-required item has no evidence. |
| `UNSAFE` | Security, reliability, or operational concern not designed for. |
| `INCONSISTENT` | SDD treatment contradicts HLD requirement or another SDD section. |
| `UNTESTABLE` | Item lacks acceptance criteria or test mapping where required. |

### The RunSkeptic triangle

```text
Ledger         = evidence structure (typed, deterministic)
Gate           = completeness rules (structural, pass/fail)
RunSkeptic     = adversarial review (judgment, attacks both)
```

RunSkeptic reviews the ledger and gate output — it is the adversarial layer,
not a replacement for the deterministic evidence and rules.

### Design principle

> HLDspec must optimize against **plausible incompleteness**: output that looks
> complete but silently drops requirements, hides assumptions, or fails to map
> design to verification.

### What we copy / what we avoid

**Copy:** stable IDs, trace links, statuses, relevant design views, rationale,
research evidence, impact awareness, inspection gates.

**Avoid:** heavy ALM bureaucracy, giant filler templates, stale manual
matrices, tool lock-in, and document appearance as success metric.

---

## 11. Non-goals

This doc does **not**:

- implement SDD generation;
- implement the coverage ledger or its schema;
- implement the completeness gate;
- call internet APIs or external tools;
- invoke SpecKit or any helper;
- mutate target repos;
- approve product decisions;
- create work orders or bridge commands;
- grant approval or implementation authority;
- replace or duplicate the existing inquiry ledger or gap register.

This is product-direction documentation only. It defines the gap, the intended
capability, and the artifacts — so that future implementation slices have a
clear target.

---

## 12. Recommended next slices

Future implementation work, in suggested order:

1. **`feat(journey2): add HLD coverage ledger contracts`** — Define the
   `HldRequirementInventory` and `HldCoverageLedger` schemas in code.
   Validation-only, no generation. Add to `prework_contracts.py` or a new
   module.

2. **`feat(journey2): add SDD completeness gate`** — Wire coverage validation
   into the existing `SOURCE_PACKAGE_APPROVAL_GATE` flow. ACTION/BLOCKED on
   incomplete coverage.

3. **`test(journey2): add synthetic HLD-to-SDD coverage scenarios`** — Synthetic
   fixtures: HLD with known items → verify inventory completeness, coverage
   mapping, and gate behavior on gaps.

4. **`feat(journey2): add research ledger integration`** — Research ledger
   schema, binding to coverage ledger items, evidence-sufficiency checks.

5. **`feat(journey2): SDD generation/packaging with coverage enforcement`** —
   Generate SDD content with mandatory coverage ledger population. Gate
   blocks on `NOT_COVERED` items. Integration with existing package builder.
