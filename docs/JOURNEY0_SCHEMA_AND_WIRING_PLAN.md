# Journey 0 Schema and Read-Only Wiring Plan

**Status:** docs plan / future implementation contract.

This doc defines planned machine-readable artifact semantics and read-only
wiring for Journey 0. It does not implement schemas, validators, discovery
execution, target mutation, SpecKit execution, backlog creation, or HLD
authoring.

Journey 0 remains a pre-HLD, read-only discovery on-ramp. Its output may support
Journey 1 HLD authoring/hardening only after evidence, conflicts, stale material,
and human-owned decisions are explicitly labeled.

## Field Semantics

These field meanings apply across all planned Journey 0 artifacts.

| Field | Semantics |
|---|---|
| `source_ref` | Stable reference to the source of evidence: file path, artifact path, human context note, or prior-state reference. It is evidence provenance, not authority. |
| `evidence_id` | Stable identifier for one evidence item in `brownfield_evidence_pack.json`. Other artifacts reference evidence by this ID. |
| `confidence` | Confidence in the classification: for example `high`, `medium`, `low`, or `unknown`. Confidence never upgrades `INFERRED` into authority. |
| `label` | Evidence label: `OBSERVED`, `INFERRED`, `UNKNOWN`, `CONFLICT`, or `PRODUCT_DECISION_REQUIRED`. |
| `status` | Artifact-local lifecycle/status value. Allowed values are defined per artifact. |
| `owner` | Human, role, or unresolved owner responsible for a decision. An unset owner is a gap, not permission for the agent to decide. |
| `decision_status` | Product decision state: `open`, `decided`, or `deferred`. |
| `gap_type` | Gap classification: `HLD_gap`, `code_gap`, `HLD_code_conflict`, `stale_spec_residue`, or `safety_authority_gap`. |
| `verdict` | Journey 0 gate verdict: `PASS`, `ACTION`, or `BLOCKED`. |
| `safe_next_action` | The next read-only or human-approved action. It must not imply implementation approval or automatic mutation. |

Rules:

- `INFERRED` is never authority by itself.
- `CONFLICT` cannot be silently resolved.
- `PRODUCT_DECISION_REQUIRED` must route to a human decision.
- `PASS` means ready for Journey 1 only, never Journey 2/3 readiness or implementation approval.

## Planned Artifacts

The filenames below are future planned filenames. This PR does not create JSON
schema files and does not create these JSON artifacts.

### Brownfield Evidence Pack

- Artifact name: Brownfield Evidence Pack
- Future file name: `brownfield_evidence_pack.json`
- Producer: future read-only Journey 0 collectors
- Consumer: Journey 0 classifiers, Draftability Verdict, HLD Update Plan, and Journey 1
- Required fields: `evidence_id`, `source_type`, `source_ref`, `source_location`, `summary`, `label`, `confidence`, `related_items`
- Field semantics: one row is one evidence claim or gap candidate; `source_ref` and `source_location` identify where it came from; `label` preserves whether it is observed, inferred, unknown, conflicted, or human-owned.
- Allowed labels/status values: labels are `OBSERVED`, `INFERRED`, `UNKNOWN`, `CONFLICT`, `PRODUCT_DECISION_REQUIRED`; no artifact status is required.
- Must not contain: unlabeled assumptions, implementation instructions, unsupported authority claims, target-write instructions.
- PASS/ACTION/BLOCKED relevance: `OBSERVED` and decided evidence can support PASS; `UNKNOWN` may be ACTION; unresolved `CONFLICT` or `PRODUCT_DECISION_REQUIRED` can BLOCK.

### Product Surface Map

- Artifact name: Product Surface Map
- Future file name: `product_surface_map.json`
- Producer: future Journey 0 classifier over accepted evidence
- Consumer: HLD Update Plan and Journey 1
- Required fields: `observed_capabilities`, `observed_users_or_actors`, `observed_inputs_outputs`, `observed_workflows`, `known_limits`, `unknowns`, `source_refs`
- Field semantics: summarizes currently observed product behavior and known uncertainty without creating new requirements.
- Allowed labels/status values: referenced evidence keeps its original labels in the Evidence Pack; map entries are concise strings and do not carry independent authority labels.
- Must not contain: feature prioritization, new requirements, unapproved target behavior, implementation slices.
- PASS/ACTION/BLOCKED relevance: enough explicit observed product shape may support PASS to Journey 1; critical unknowns remain ACTION or BLOCKED depending on ownership. PASS must not be based merely on the existence of observed files.

### Spec Inventory

- Artifact name: Spec Inventory
- Future file name: `spec_inventory.json`
- Producer: future read-only collector/classifier for old specs and prior `.specify` state
- Consumer: Gap Report, Product Decision Register, HLD Update Plan
- Required fields: `spec_id`, `location`, `status`, `summary`, `covered_intent`, `implementation_overlap`, `conflicts`, `source_refs`
- Field semantics: records old spec material as evidence and classifies its relationship to current product state.
- Allowed labels/status values: `current`, `stale`, `superseded`, `partial`, `conflicting`, `unknown`
- Must not contain: new backlog order, automatic preservation of old SpecKit boundaries, implementation approval.
- PASS/ACTION/BLOCKED relevance: current evidence may feed Journey 1; stale/superseded/partial/conflicting specs must not become backlog or authority without later Journey 1/2 processing and human approval.

### HLD-Code-Spec Gap Report

- Artifact name: HLD-Code-Spec Gap Report
- Future file name: `hld_code_spec_gap_report.json`
- Producer: future Journey 0 classifier
- Consumer: Draftability Verdict, Product Decision Register, HLD Update Plan
- Required fields: `gap_id`, `gap_type`, `description`, `evidence_refs`, `disposition`, `required_decision_or_next_action`
- Field semantics: every gap states what disagrees or is missing, the evidence behind it, and what must happen next.
- Allowed labels/status values: gap types are `HLD_gap`, `code_gap`, `HLD_code_conflict`, `stale_spec_residue`, `safety_authority_gap`; disposition may be `continue_discovery`, `route_to_journey1`, `human_decision_required`, or `block_before_handoff`.
- Must not contain: silent conflict resolution, implementation plan, SpecKit spec generation.
- PASS/ACTION/BLOCKED relevance: fixable missing evidence can be ACTION; unresolved conflicts or safety/authority gaps are BLOCKED.

### Product Decision Register

- Artifact name: Product Decision Register
- Future file name: `product_decision_register.json`
- Producer: future Journey 0 classifier
- Consumer: Draftability Verdict, HLD Update Plan, human owner
- Required fields: `decision_id`, `question`, `why_human_owned`, `options`, `evidence_refs`, `recommended_default_if_any`, `decision_status`, `owner`
- Field semantics: records human-owned decisions explicitly and preserves whether they are open, decided, or deferred.
- Allowed labels/status values: decision status is `open`, `decided`, or `deferred`.
- Must not contain: agent-approved product decisions, hidden defaults for architecture/source-of-truth/security/data/user-visible scope.
- PASS/ACTION/BLOCKED relevance: open human-owned decisions that affect HLD authority are BLOCKED; decided items can pass to Journey 1 as explicit product decisions.

### HLD Draftability Verdict

- Artifact name: HLD Draftability Verdict
- Future file name: `hld_draftability_verdict.json`
- Producer: future Journey 0 verdict computation
- Consumer: human owner and Journey 1
- Required fields: `verdict`, `reason`, `blocking_items`, `accepted_evidence_refs`, `required_human_decisions`, `safe_next_action`
- Field semantics: summarizes whether Journey 1 may responsibly author or harden an authoritative HLD.
- Allowed labels/status values: verdict is `PASS`, `ACTION`, or `BLOCKED`.
- Must not contain: implementation readiness claim, Journey 2 package readiness claim, Journey 3 helper readiness claim.
- PASS/ACTION/BLOCKED relevance: this is the Journey 0 gate result. PASS means Journey 1 may proceed from accepted evidence and explicit decisions only.

### HLD Update Plan

- Artifact name: HLD Update Plan
- Future file name: `hld_update_plan.json`
- Producer: future Journey 0 planner from accepted evidence and explicit decisions
- Consumer: Journey 1
- Required fields: `hld_sections_to_create_or_update`, `evidence_refs_per_section`, `decisions_required_before_writing`, `known_stale_material_to_exclude`, `open_questions_to_carry_forward`
- Field semantics: maps accepted Journey 0 outputs into the HLD work Journey 1 may perform.
- Allowed labels/status values: section inputs reference evidence labels and decision statuses; no independent gate status is required.
- Must not contain: backlog, SpecKit specs, implementation slices, helper handoff.
- PASS/ACTION/BLOCKED relevance: PASS requires the plan to be bounded, evidence-referenced, and free of hidden conflicts.

## Read-Only Wiring Plan

Future Journey 0 implementation may read evidence from:

- existing code and tests,
- existing docs,
- old SpecKit specs and `.specify` state,
- prior `.hldspec` state,
- HLD fragments,
- human-provided context.

All inputs are read-only evidence. The wiring may collect, label, classify, and
report. It must not mutate the target repo, invoke SpecKit, create backlog,
write the Journey 1 HLD, create Journey 2 spec bites, perform Journey 3 helper
handoff, or make automatic product decisions.

## Data Flow

```text
mixed target resources
  -> read-only collectors
  -> labeled evidence
  -> product surface mapping
  -> gap / spec / decision classification
  -> HLD Draftability Verdict
  -> HLD Update Plan
  -> Journey 1
```

Blocked path:

```text
CONFLICT / PRODUCT_DECISION_REQUIRED / safety_authority_gap
  -> Product Decision Register
  -> human decision before Journey 1 PASS
```

## Future Implementation Slices

Each slice must remain separately reviewable and must not smuggle in the next
slice.

### Slice A: schema dataclasses / typed artifact models only

- Input: this docs plan and `JOURNEY0_BROWNFIELD_DISCOVERY.md`
- Output: typed in-memory models for planned artifacts
- Forbidden behavior: filesystem reads, target inspection, validators that claim production readiness, SpecKit execution
- Validation/check: synthetic construction tests for required fields and allowed labels/statuses

### Slice B: read-only collectors for target resources

- Input: authorized target/resource paths and typed models
- Output: raw evidence candidates with `source_ref`
- Forbidden behavior: target mutation, broad unbounded scans, SpecKit invocation, backlog/HLD writing
- Validation/check: fixture-based read-only tests proving no files are changed

### Slice C: classifier from raw evidence to labels/gaps/decisions

- Input: raw evidence candidates
- Output: labeled Evidence Pack, Spec Inventory, Gap Report, and Product Decision Register
- Forbidden behavior: silent conflict resolution, product decisions, implementation planning
- Validation/check: tests for `INFERRED`, `CONFLICT`, `UNKNOWN`, and `PRODUCT_DECISION_REQUIRED` preservation

### Slice C2: Product Surface Map builder/classifier

- Input: typed Evidence Pack with explicit product-surface evidence
- Output: Product Surface Map
- Forbidden behavior: product inference from arbitrary file presence, authority claims from old specs/HLD fragments, draftability verdicts, HLD Update Plan generation
- Validation/check: tests that only explicit `OBSERVED` product-surface evidence populates observed product fields

### Slice D1: draftability verdict computation

- Input: Product Surface Map, Gap Report, Product Decision Register, and accepted evidence
- Output: HLD Draftability Verdict only
- Forbidden behavior: HLD Update Plan generation, Journey 2 package readiness, Journey 3 helper readiness, implementation approval
- Validation/check: PASS/ACTION/BLOCKED tests including blocked human-owned decisions and product-surface sufficiency

Draftability PASS requires enough explicit product-surface evidence, no unresolved
human-owned decisions, and no blocking gaps. PASS means ready for Journey 1 only;
it does not mean Journey 2, Journey 3, SpecKit, implementation, or target
mutation readiness.

### Slice D2: HLD Update Plan generation

- Input: PASS/ACTION draftability result, Product Surface Map, accepted evidence, explicit decisions, and labeled stale/superseded material
- Output: HLD Update Plan
- Forbidden behavior: backlog creation, SpecKit spec generation, implementation slices, helper handoff
- Validation/check: plan sections are evidence-referenced and do not hide conflicts or unresolved human-owned decisions

### Slice E: dry-run proof on authorized brownfield target

- Input: explicit human-approved read-only target and resources
- Output: Journey 0 artifacts only
- Forbidden behavior: target mutation, backlog creation, HLD writing, SpecKit execution, implementation
- Validation/check: before/after target snapshot, artifact-only output, and at least one PASS/ACTION/BLOCKED example backed by labeled evidence

## Context-Aware Follow-Up Issues

These issues are recorded so they are not dropped, but they are not implemented
by this plan update:

1. Human context evidence adapter: Journey 0 inputs include human-provided context, but current collectors only read filesystem paths. Add a later read-only adapter that turns explicit human notes into typed EvidenceItem rows.
2. Bounded EvidenceSourceType: EvidenceItem.source_type is currently a plain string. Consider a bounded enum or central constants after the ProductSurfaceMap and verdict path stabilize.
3. Snippet privacy before real-target dry run: the read-only collector may include bounded first-line metadata. Before Slice E or any real target proof, decide whether snippets must be disabled by default, redacted, or made opt-in.
4. Boundary-token tests: current boundary tests should avoid incentivizing artificial string splitting such as avoiding a literal `.git` token. Later replace broad token bans with behavior/import/write-safety checks.
5. Product-surface sufficiency: future draftability verdict must check product-surface sufficiency, not merely the existence of observed files.
6. Status documentation: after Slice D1/D2/E stabilize, update Journey 0 status docs so implemented slices and planned slices are not confused.

## Dry-Run Proof Expectations

A Journey 0 dry-run proof must produce artifacts only. It must not change the
target repo, create backlog, write an HLD, invoke SpecKit, or implement. It must
show at least one PASS, ACTION, or BLOCKED example using labeled evidence.

The proof report must include:

- target/resource scope that was approved,
- artifacts produced,
- evidence labels used,
- whether any `CONFLICT`, `PRODUCT_DECISION_REQUIRED`, or `safety_authority_gap` blocked PASS,
- target before/after mutation check,
- next human action.
