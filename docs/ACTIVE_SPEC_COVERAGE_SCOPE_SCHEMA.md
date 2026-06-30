# Active-Spec Coverage-Scope Schema

**Status:** Docs-only schema/contract. No runtime enforcement.

**Non-goals:**

- No Python validators.
- No producer changes.
- No `hld_coverage_ledger.json` shape change.
- No `speckit_single_spec_input.md` changes.
- No renderer wiring.
- No source-package generation changes.
- No manifest changes.
- No gate/readiness/driver behavior changes.
- No SpecKit/Baton behavior changes.
- No target writes.

---

## 1. Compatibility constraint

The existing `hld_coverage_ledger.json` is a generated artifact with established
behavior. Its top-level shape is a bare JSON array of coverage-item dicts.
Readers, validators, fixtures, and gates depend on this shape.

**Required rule:** the first implementation must not silently change the
top-level shape of `hld_coverage_ledger.json` unless all readers, validators,
fixtures, and gates are migrated in the same explicit compatibility slice.

---

## 2. Problem

Full-HLD coverage and active-spec coverage answer different questions:

- **Full-HLD mode** asks: "Does the generated full single-spec input cite every
  required HLD anchor?"
- **Active-spec mode** asks: "Does the selected active spec input cite the HLD
  anchors claimed by that selected spec?"

Non-selected anchors are intentionally out of scope in active-spec mode.

Existing `NOT_COVERED` semantics are unsafe without scope metadata because a
gate cannot distinguish "anchor missing from selected spec by design" from
"anchor accidentally dropped from full-HLD input."

---

## 3. Core concepts

```
coverage_scope = FULL_HLD | ACTIVE_SPEC
```

| Value | Meaning |
|---|---|
| `FULL_HLD` | Coverage evaluated against the whole HLD reference map. Every anchor is in scope. |
| `ACTIVE_SPEC` | Coverage evaluated against one selected active spec's claimed HLD anchors. Non-selected anchors are intentionally out of scope. |

---

## 4. Recommended minimal artifact

The lowest-risk first implementation is a **sidecar artifact**, not a breaking
change to the existing ledger:

```
.hldspec/source_package/hld_coverage_scope.json
```

**Why a sidecar:**

- Avoids breaking the current bare-list ledger shape.
- Lets future code bind coverage interpretation to mode.
- Gives gates a safe way to distinguish full-HLD and active-spec coverage.
- Can later be folded into a v2 ledger object if explicitly migrated.

---

## 5. Sidecar schema

Future JSON shape:

```json
{
  "schema_version": 1,
  "coverage_scope": "FULL_HLD",
  "active_spec_id": null,
  "selected_hld_anchor_ids": [],
  "source_refs": [],
  "notes": []
}
```

### Field rules

| Field | Type | Rules |
|---|---|---|
| `schema_version` | integer | Must be `1`. |
| `coverage_scope` | string | Required. Exactly `"FULL_HLD"` or `"ACTIVE_SPEC"`. |
| `active_spec_id` | string or null | Must be `null` when `coverage_scope == "FULL_HLD"`. Must be non-empty string when `coverage_scope == "ACTIVE_SPEC"`. |
| `selected_hld_anchor_ids` | list of strings | Empty or full reference-map anchor list in `FULL_HLD`. Non-empty list of selected spec's `hld_anchor_ids` in `ACTIVE_SPEC`. Values must be unique. |
| `source_refs` | list of strings | Provenance references. |
| `notes` | list of strings | Free-text notes. |

---

## 6. Interpretation rules

### FULL_HLD

In `FULL_HLD` mode, `NOT_COVERED` rows in `hld_coverage_ledger.json` remain
blocking candidates because the full HLD is expected to be represented.

### ACTIVE_SPEC

In `ACTIVE_SPEC` mode:

- `NOT_COVERED` rows **outside** `selected_hld_anchor_ids` must not be treated
  as accidental disappearance. They are intentionally out of scope.
- Rows **inside** `selected_hld_anchor_ids` may still block if `NOT_COVERED` —
  these are anchors the selected spec claims to cover.
- Rows outside selected anchors may produce advisory warnings but not gate
  blockers.
- Gate wiring must not simply disable coverage in active-spec mode.

---

## 7. Gate boundary

**Rule 1:** No gate may consume active-spec-rendered
`speckit_single_spec_input.md` as full-HLD coverage evidence unless
`coverage_scope` is `FULL_HLD`.

**Rule 2:** Before `SOURCE_PACKAGE_APPROVAL_GATE` uses active-spec-rendered
input, it must understand `hld_coverage_scope.json` or equivalent
coverage-scope metadata.

---

## 8. Future implementation sequence

1. Define active-spec coverage-scope schema. *(this PR)*
2. Add pure `hld_coverage_scope` validator.
3. Emit `hld_coverage_scope.json` in `FULL_HLD` mode without changing behavior.
4. Add `ACTIVE_SPEC`-mode scope generation from selected spec backlog.
5. Update coverage ledger interpretation to separate selected-anchor blockers
   from out-of-scope advisory rows.
6. Wire active-spec renderer into source-package generation only behind explicit
   active-spec mode.
7. Add materialization receipt.
8. Only then consider gate/readiness integration.

---

## 9. Relationship to existing docs

| Doc | Relationship |
|---|---|
| [`ACTIVE_SPEC_SOURCE_PACKAGE_RENDERING_CONTRACT.md`](ACTIVE_SPEC_SOURCE_PACKAGE_RENDERING_CONTRACT.md) | Identifies the coverage-scope risk. This schema defines the artifact that resolves it. |
| [`MULTI_SPEC_BACKLOG_AND_ACTIVE_SELECTION.md`](MULTI_SPEC_BACKLOG_AND_ACTIVE_SELECTION.md) | Defines the spec backlog and active selection. The `active_spec_id` and `selected_hld_anchor_ids` in this schema trace back to that backlog. |
| [`JOURNEY2_READINESS_GATE_INVENTORY.md`](JOURNEY2_READINESS_GATE_INVENTORY.md) | Maps enforceable-now vs defined-but-not-wired contracts. This schema is defined-but-not-wired. |
| [`HLDSPEC_GAP_AND_OPEN_ISSUES_INVENTORY.md`](HLDSPEC_GAP_AND_OPEN_ISSUES_INVENTORY.md) | Tracks gaps. The coverage-scope distinction is one such gap. |
| [`CONTEXT_SAFETY_AND_GAP_CONTINUITY.md`](CONTEXT_SAFETY_AND_GAP_CONTINUITY.md) | Bounded decomposition doctrine. Active-spec coverage scoping is one realization. |
