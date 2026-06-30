# Active-Spec Source-Package Rendering Contract

**Status:** Docs-only contract. No runtime enforcement.

**Non-goals:**

- No source-package generation wiring.
- No renderer wiring.
- No `speckit_single_spec_input.md` writes.
- No `spec_backlog.json` mutation.
- No active selection.
- No materialization receipt.
- No gate/readiness changes.
- No driver changes.
- No SpecKit/Baton changes.
- No target writes.

---

## 1. Problem

Current source-package flow assumes `speckit_single_spec_input.md` can represent
the complete HLD-derived SpecKit input. The SDD Completeness Gate
(`JOURNEY2_SDD_COMPLETENESS_GATE.md`) and HLD Coverage Ledger
(`journey2_hld_coverage_contracts.py`) track every HLD item and block on
`NOT_COVERED` items.

Multi-spec mode changes this:

- One HLD can produce many candidate specs via the spec backlog
  (`spec_backlog.json`).
- Only one selected active spec should be rendered at a time.
- Rendering one active spec intentionally excludes non-selected backlog
  candidates and their HLD anchors.
- Therefore full-HLD `NOT_COVERED` semantics may become unsafe if interpreted as
  source-package failure when the system is in active-spec mode.

---

## 2. Core invariant

When active-spec mode is enabled, `speckit_single_spec_input.md` represents
exactly one selected active spec, not the full HLD backlog.

The selected active spec may be target-facing through the existing single SpecKit
input path, but non-selected backlog candidates must not be rendered or
materialized.

---

## 3. Required backlog state before rendering

Rendering is allowed only when all of the following hold:

- `spec_backlog.json` validates (passes `validate_spec_backlog`).
- `active_spec_id` is non-null.
- Exactly one spec has status `SELECTED`.
- Selected spec `target_materialization` is `NOT_MATERIALIZED`.
- Selected spec `size_class` is not `TOO_LARGE`.
- Selected spec has non-empty `validation_strategy`.
- Selected spec dependencies are `DONE` or `VALIDATED`.
- No other candidate is `SELECTED` or `MATERIALIZED_TO_TARGET`.

The renderer (`render_active_spec_to_single_spec_input` in
`hldspec/spec_backlog.py`) fails closed on an invalid backlog, a missing or
non-`SELECTED` active spec, or an already-materialized spec. The remaining
preconditions (size class, validation strategy, dependency state) are enforced
transitively through `validate_spec_backlog`, which the renderer calls before
rendering.

---

## 4. Rendering behavior

The future renderer wiring must:

- Use `render_active_spec_to_single_spec_input`.
- Write only the selected active spec into the existing single SpecKit input
  path (`speckit_single_spec_input.md`).
- Preserve HLD anchor traceability (the rendered output includes `hld_anchor_ids`
  from the selected spec).
- Include HLD anchor citations in a form recognized by the coverage ledger, if
  coverage is evaluated.
- Exclude all non-selected backlog candidates from the rendered output.
- Not change `target_materialization` state by itself (that is a separate
  lifecycle step).
- Not mark status `MATERIALIZED_TO_TARGET`.
- Not create implementation files.

---

## 5. Coverage / gate interaction

This is the critical risk section.

### The problem

A full-HLD coverage ledger and an active-spec-scoped input answer different
questions:

| Mode | What `NOT_COVERED` means |
|---|---|
| **Full-HLD mode** | An HLD anchor is missing from the generated single full-HLD input. The gate may block — this is the correct behavior. |
| **Active-spec mode** | Non-selected HLD anchors are intentionally outside the selected active spec. `NOT_COVERED` for those anchors is expected, not accidental. Treating it as a blocker would be incorrect. |

### The distinction

In full-HLD mode, `NOT_COVERED` means an HLD item was accidentally dropped from
the generated spec input. The coverage ledger and SDD Completeness Gate
(`blocking_items` in `journey2_hld_coverage_contracts.py`) correctly treat this
as a blocking status.

In active-spec mode, non-selected HLD anchors are outside the scope of the
current active spec by design. They belong to other backlog candidates that will
be rendered in future iterations. `NOT_COVERED` for these anchors must not be
treated as accidental disappearance.

### Required future rule

Before active-spec rendering is wired into any gate-bearing source-package path,
HLD coverage semantics must distinguish full-HLD coverage from
selected-active-spec coverage.

Without this distinction, wiring the renderer into the source-package path risks:

- False-positive blocking: the gate blocks because non-selected anchors appear
  as `NOT_COVERED`.
- False-negative bypass: disabling the gate entirely to avoid false positives
  would lose coverage enforcement for the anchors that *should* be covered by
  the selected spec.

---

## 6. Future artifact / field options

Possible future approaches (not implemented by this contract):

- `coverage_scope: "FULL_HLD" | "ACTIVE_SPEC"` field on the coverage ledger or
  completeness report, indicating which mode the coverage check applies to.
- `active_spec_id` in coverage ledger metadata, binding the ledger to a specific
  active spec selection.
- Selected-anchor-only coverage ledger variant that validates only the HLD
  anchors claimed by the selected active spec.
- Separate `active_spec_materialization_receipt.json` recording what was rendered
  and when.
- Advisory warning when non-selected anchors are outside the current active spec,
  without blocking.

The smallest likely next code slice is adding a `coverage_scope` field to the
completeness report that downstream gates can inspect.

---

## 7. Minimal future implementation sequence

1. Define active-spec rendering contract (this PR).
2. Add active-spec coverage-scope contract/schema.
3. Add pure coverage-scope validator or metadata support.
4. Wire renderer into source-package generation only behind explicit active-spec
   input.
5. Add materialization receipt.
6. Only then consider readiness/gate integration.

---

## 8. Relationship to existing docs

| Doc | Relationship |
|---|---|
| [`MULTI_SPEC_BACKLOG_AND_ACTIVE_SELECTION.md`](MULTI_SPEC_BACKLOG_AND_ACTIVE_SELECTION.md) | Defines the spec backlog schema, candidate statuses, selection rules, and the core invariant (many candidates, at most one active). This contract builds on that foundation to address the rendering/coverage interaction. |
| [`JOURNEY2_SDD_COMPLETENESS_GATE.md`](JOURNEY2_SDD_COMPLETENESS_GATE.md) | Defines HLD coverage ledger and `NOT_COVERED` blocking semantics. This contract identifies the coverage-scope conflict that active-spec mode creates. |
| [`CONTEXT_SAFETY_AND_GAP_CONTINUITY.md`](CONTEXT_SAFETY_AND_GAP_CONTINUITY.md) | Doctrine establishing bounded decomposition. Active-spec rendering is one realization of that doctrine: decompose into bounded specs, render one at a time. |
| [`HLDSPEC_GAP_AND_OPEN_ISSUES_INVENTORY.md`](HLDSPEC_GAP_AND_OPEN_ISSUES_INVENTORY.md) | Gaps inventory. The coverage-scope distinction identified here is a new gap that should be tracked. |
| [`JOURNEY2_PACKAGE_CONTRACT.md`](JOURNEY2_PACKAGE_CONTRACT.md) | Defines the structural package gate (`SOURCE_PACKAGE_APPROVAL_GATE`). Active-spec rendering must eventually integrate with this gate under the correct coverage scope. |
