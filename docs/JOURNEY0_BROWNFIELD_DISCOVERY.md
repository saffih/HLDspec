# Journey 0 — Brownfield Product Discovery / HLD Gap Assessment

**Status:** docs contract. This doc defines the *contract and boundary* of a
pre-HLD discovery journey for brownfield products. It defines gate states,
artifact shapes, handoff rules, and disconfirming checks, but it does **not**
add runtime validators, schemas, target mutation, SpecKit execution, or
implementation behavior. Those are explicit future steps (see
[§12 Status and next steps](#12-status-and-next-steps)).

> Relationship to the canonical doc:
> [`HLDSPEC_TERMINOLOGY_AND_FLOW.md`](HLDSPEC_TERMINOLOGY_AND_FLOW.md) remains
> authoritative on terminology, ownership, and mechanics and **wins on any
> conflict**. This doc adds a pre-HLD on-ramp ahead of the existing three
> journeys; it does not renumber them or change runtime behavior.

---

## 1. What Journey 0 is, and where it sits

Journey 0 is a **pre-HLD discovery journey for brownfield products**. It runs
*before* Journey 1, when a target already contains some combination of code,
specs, docs, HLD fragments, `.specify/` state, `.hldspec/` state, or blocked
implementation history — and those inputs may be incomplete, stale, or
contradictory.

It answers one question:

> **What evidence exists, what conflicts, what is missing, and can an
> authoritative HLD responsibly be written?**

Journey 0 is an **on-ramp into Journey 1, not a fourth peer journey** and not a
renumbering. The product is still the three journeys
([`THREE_JOURNEYS.md`](THREE_JOURNEYS.md)); Journey 0 precedes and feeds the
first one:

```text
(brownfield target: code / specs / docs / HLD fragments / .specify / .hldspec)
        │
        ▼
┌──────────────────────────────────────────────┐
│ Journey 0 — Brownfield Discovery / Gap Assess │  read-only; produces evidence + decisions
└──────────────────────────────────────────────┘
        │  produces:  accepted evidence + explicit product decisions + HLD Update Plan
        ▼
   Source HLD (read-only)  ──►  Journey 1 ──► Journey 2 ──► Journey 3
   (authored / hardened from Journey 0 output)
```

For brownfield products such as **Baton Flow** (`~/code/flow`), Journey 0 is the
correct entry point before attempting to create or update the authoritative HLD.
`~/code/flow` is the **motivating proving-ground**, not a target to run now —
this doc defines the journey; it does not execute against any repo.

## 2. Why this is before Journey 1, not part of Journey 1

Journey 1 and Journey 0 ask different questions:

| | Question |
|---|---|
| **Journey 0** | What evidence exists, what conflicts, what is missing, and can an authoritative HLD *responsibly be written*? |
| **Journey 1** | Is the HLD itself clear, complete, and SDD-ready? |

Journey 1 assumes there is a candidate HLD to judge. On a brownfield product that
assumption fails: there may be several partial, stale, or contradictory sources
and no single authority. Folding discovery into Journey 1 would force the HLD
gate to silently pick winners among conflicting evidence — exactly the product
decision that must stay with a human. Journey 0 surfaces those conflicts and the
required decisions first, so Journey 1 can then author or harden **one**
authoritative HLD from *accepted* evidence and *explicit* decisions.

In Journey 0, existing code, specs, docs, and HLD fragments are **evidence, not
automatic authority**. When they conflict, Journey 0 classifies the conflict and
surfaces a product decision instead of silently choosing a winner.

## 3. Relationship to the existing brownfield boundary

HLDspec already states that **arbitrary brownfield *adoption* is unsupported** —
HLDspec will not silently treat existing, untrusted code as if it had HLDspec
lineage and proceed toward implementation
([`HLDSPEC_TERMINOLOGY_AND_FLOW.md`](HLDSPEC_TERMINOLOGY_AND_FLOW.md) glossary;
enforced in `hldspec/target_discovery.py` via the `UNKNOWN_BROWNFIELD`
classification and in `hldspec/product_runability.py`).

**Journey 0 does not lift or relax that restriction.** It adds a *read-only
assessment step ahead of it*: it inspects and reports, then a human decides
whether and how to feed the result into Journey 1. This is continuous with the
read-only brownfield primitives HLDspec already ships — the `UNKNOWN_BROWNFIELD`
discovery/classification in `hldspec/target_discovery.py` and the read-only
"where are we?" aggregator `hldspec/journey3_driver.py` /
`scripts/hldspec_journey3_status.py`. Journey 0 is the product framing those
read-only inspectors point toward; it proposes no change to them here.

## 4. Inputs

Everything already present in or around the brownfield target, treated as
evidence:

- existing source code and tests,
- existing specs (`.specify/`, `specs/`) and any blocked implementation history,
- existing docs and design notes,
- HLD fragments (whole or partial, current or stale),
- prior `.hldspec/` state and discovery/classification output,
- human knowledge offered during discovery.

## Resource discovery trigger

A user may start from mixed resources rather than a clean HLD.

Convenience alias:

```text
HLD discover target <target-repo> from <resources/context>
```

This is Journey 0-style read-only discovery. It treats all resources as
evidence, not authority.

Resources may include old SpecKit specs, existing code/tests, docs, design
notes, HLD fragments, prior `.specify` state, prior `.hldspec` state, and human
context.

Journey 0 classifies evidence, conflicts, stale parts, missing decisions, and
whether an authoritative HLD can responsibly be drafted.

Journey 0 must not create backlog, create SpecKit specs, mutate the target repo,
invoke SpecKit, or implement.

### Old SpecKit specs

Old SpecKit specs are evidence, not authority.

HLDspec must not preserve old SpecKit spec boundaries by default. Old specs may
be stale, oversized, mixed, partially implemented, or inconsistent with the
current target repo.

Journey 0 should classify old spec content into product intent, existing
behavior, desired behavior, implementation detail, stale assumption, dependency,
acceptance criterion, test expectation, migration/compatibility concern, and
open human decision.

Old spec content may feed the Evidence Pack, Spec Inventory, Gap Report,
Product Decision Register, and HLD Update Plan. It must not directly become the
new backlog.

## 5. Gate states

Journey 0 emits one of three gate states:

| State | Meaning |
|---|---|
| **PASS** | Enough accepted evidence and explicit product decisions exist to responsibly draft or harden an authoritative HLD in Journey 1. |
| **ACTION** | Specific fixable discovery gaps remain, but no unresolved human-owned product/authority conflict blocks progress. Journey 0 may continue read-only discovery or ask for specific missing evidence. |
| **BLOCKED** | An authoritative HLD cannot responsibly be drafted because product intent, source of truth, authority, HLD-code-spec conflicts, safety boundary, or ownership decisions are unresolved. |

**PASS does not mean implementation-ready.** PASS only means Journey 1 may
author or harden the HLD from accepted evidence and explicit decisions. It does
not mean Journey 2 package readiness, Journey 3 helper readiness, SpecKit
readiness, or implementation approval.

## 6. What may pass to Journey 1

Journey 0 may pass to Journey 1 only:

- accepted evidence,
- explicit product decisions,
- unresolved questions clearly labeled,
- stale/superseded material clearly labeled,
- HLD Update Plan,
- HLD Draftability Verdict.

Journey 0 must not pass raw mixed resources as authority. Journey 0 must not
pass old SpecKit specs as new backlog. Journey 0 must not pass inferred product
truth without labeling it `INFERRED`. Journey 0 must not hide conflicts inside a
draft HLD.

Journey 0 does not create right-sized spec bites. Journey 0 prepares the
accepted evidence and HLD Update Plan. Journey 1 creates or hardens the HLD.
Journey 2 creates right-sized spec bites.

## 7. Artifact shapes

Journey 0 **may produce** the following artifacts. These are lightweight docs
contract shapes, not JSON schemas or runtime validators.

### Brownfield Evidence Pack

Purpose: collect and label evidence from all inputs.

Required fields: `evidence_id`, `source_type`, `source_location`, `summary`,
`label` (`OBSERVED` / `INFERRED` / `UNKNOWN` / `CONFLICT` /
`PRODUCT_DECISION_REQUIRED`), `confidence`, `related_items`.

Must not contain: unlabeled assumptions, implementation instructions, authority
claims not supported by evidence.

Gate relevance: supports PASS only when material claims are accepted evidence or
explicit decisions; `CONFLICT`, `UNKNOWN`, and `PRODUCT_DECISION_REQUIRED` drive
ACTION or BLOCKED.

### Product Surface Map

Purpose: summarize what the product appears to do from accepted evidence.

Required fields: `observed_capabilities`, `observed_users_or_actors`,
`observed_inputs_outputs`, `observed_workflows`, `known_limits`, `unknowns`,
`source_refs`.

Must not contain: new product requirements, feature prioritization, unapproved
target behavior.

Gate relevance: identifies whether Journey 1 has enough observed product shape
to draft or harden the HLD.

### Spec Inventory

Purpose: classify existing specs/spec-fragments and their relationship to the
current target.

Required fields: `spec_id`, `location`, `status` (`current` / `stale` /
`superseded` / `partial` / `conflicting` / `unknown`), `summary`,
`covered_intent`, `implementation_overlap`, `conflicts`, `source_refs`.

Must not contain: new backlog order, automatic preservation of old spec
boundaries, implementation approval.

Gate relevance: stale, superseded, partial, conflicting, or unknown specs must
not become authority or backlog without Journey 1/2 processing and human
approval.

### HLD-Code-Spec Gap Report

Purpose: show where HLD, code, and specs agree, diverge, or are silent.

Required fields: `gap_id`, `gap_type` (`HLD_gap` / `code_gap` /
`HLD_code_conflict` / `stale_spec_residue` / `safety_authority_gap`),
`description`, `evidence_refs`, `disposition`,
`required_decision_or_next_action`.

Must not contain: silent conflict resolution, implementation plan, spec
generation.

Gate relevance: fixable evidence gaps may be ACTION; unresolved conflicts or
safety/authority gaps are BLOCKED.

### Product Decision Register

Purpose: list product, authority, source-of-truth, safety, data, and ownership
questions that require a human decision.

Required fields: `decision_id`, `question`, `why_human_owned`, `options`,
`evidence_refs`, `recommended_default_if_any`, `status` (`open` / `decided` /
`deferred`), `owner`.

Must not contain: agent-approved product decisions, hidden defaults for
architecture/source-of-truth/security/data/user-visible scope.

Gate relevance: open human-owned decisions that affect authoritative HLD content
are BLOCKED; decided items may feed Journey 1 as explicit product decisions.

### HLD Draftability Verdict

Purpose: state whether an authoritative HLD can responsibly be drafted or
hardened yet.

Required fields: `verdict` (`PASS` / `ACTION` / `BLOCKED`), `reason`,
`blocking_items`, `accepted_evidence_refs`, `required_human_decisions`,
`safe_next_action`.

Must not contain: implementation readiness claim, Journey 2 package readiness
claim, Journey 3 helper readiness claim.

Gate relevance: this is the Journey 0 gate output. PASS means ready to enter
Journey 1 only.

### HLD Update Plan

Purpose: tell Journey 1 what to author or harden from accepted evidence and
explicit decisions.

Required fields: `hld_sections_to_create_or_update`,
`evidence_refs_per_section`, `decisions_required_before_writing`,
`known_stale_material_to_exclude`, `open_questions_to_carry_forward`.

Must not contain: backlog, SpecKit specs, implementation slices, helper handoff.

Gate relevance: PASS requires a bounded update plan whose inputs are accepted
evidence, explicit decisions, and clearly labeled unknowns.

## 8. Evidence labels

Every material finding in Journey 0 is classified:

- **OBSERVED** — directly present in code, specs, docs, or state.
- **INFERRED** — reasonably derived from evidence, not directly stated.
- **UNKNOWN** — not determinable from available evidence; a gap.
- **CONFLICT** — sources disagree; no silent winner.
- **PRODUCT_DECISION_REQUIRED** — resolving it needs a human product decision, not more inspection.

## 9. Gap handling rules

Journey 0 routes each gap; it does not resolve product or authority conflicts
itself:

| Gap kind | Disposition |
|---|---|
| **HLD gap** (HLD missing/incomplete) | → **Journey 1** (author/harden the HLD). |
| **Code gap** (HLD/spec intent not yet built) | → later **implementation** (Journey 2 → Journey 3), never inside Journey 0. |
| **HLD–code conflict** | → **product decision** (Product Decision Register; `PRODUCT_DECISION_REQUIRED`). |
| **Stale spec residue** | → mark **stale / superseded** in the Spec Inventory; do not treat as authority. |
| **Safety / authority gap** | → **block before implementation**; a missing owner/authority is not auto-resolved. |

## 10. Disconfirming checks

Journey 0 must fail safely on these cases:

- **BLOCKED case:** code, docs, and old specs disagree about the source of truth
  for run state, and no human decision resolves it.
- **Stale SpecKit case:** an old SpecKit spec describes an oversized or partially
  implemented feature; it is classified as stale/partial evidence and must not
  become the new backlog.
- **HLD-only readiness case:** observed evidence and decisions are enough to
  draft an HLD, but no right-sized package, tests, or helper handoff exists;
  Journey 0 may PASS to Journey 1 but must not claim implementation readiness.
- **Contradiction case:** code behavior contradicts docs; Journey 0 records an
  `HLD_code_conflict` and asks for a product decision instead of choosing a
  winner.
- **Inference case:** a plausible product claim is derived from naming or
  structure only; it remains `INFERRED` and cannot become authority without
  evidence or decision.

## 11. Non-goals (hard boundaries)

Journey 0 **must not**:

- mutate the target repo,
- create or modify `.specify/`,
- create or modify target `.hldspec/`,
- invoke SpecKit,
- approve protected transitions,
- produce implementation work orders,
- silently resolve product or authority conflicts.

Journey 0 is read-only discovery and assessment. It identifies evidence, gaps,
stale inputs, conflicts, and required product decisions, then **hands off to
Journey 1** — which may author or harden the authoritative HLD from accepted
evidence and explicit decisions.

## 12. Status and next steps

This doc is a **docs contract only**. It intentionally does **not**:

- implement code or a discovery machine,
- define JSON schemas or runtime validators,
- run against any target repo (including `~/code/flow`),
- change Journeys 1–3 or their contracts.

The planned machine-readable artifact semantics and read-only wiring path are
defined in [`JOURNEY0_SCHEMA_AND_WIRING_PLAN.md`](JOURNEY0_SCHEMA_AND_WIRING_PLAN.md).

Natural next steps, each a separate gated change:

1. **Convert planned artifact semantics into actual schema/dataclass code.**
2. **Wire read-only collectors** (`target_discovery.py`,
   `journey3_driver.py`) without granting any mutation or adoption authority.
3. **Run the first authorized read-only proof** on a brownfield proving-ground
   (e.g. Baton Flow), once the above are gated.
