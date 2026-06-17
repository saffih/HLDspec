# Journey 2 — Inquiry/Gap Ledger and Lens Registry Contract

**Status:** design contract (docs only). No runtime implementation yet. Extends
`docs/JOURNEY2_PACKAGE_CONTRACT.md` §5 and §15. Implementation slices tracked in
`docs/HLDSPEC_DEVELOPMENT_BACKLOG.md::P1-013`.

---

## 1. Purpose

Journey 2 compiles an SDD-ready HLD. Before the package can be trusted, it must
surface its epistemic state: what it asked, what it resolved, what it assumed, and
what it cannot answer without a human. The existing package artifacts
(`hld_reference_map.json`, `speckit_single_spec_input.md`, `implementation_slices.json`)
answer *what to build*. The inquiry/gap artifacts answer *what was unknown going in,
and what remains open*.

Two canonical artifacts:
- **`inquiry_ledger.json`** — every question Journey 2 raised, its status, and what
  it binds to.
- **`gap_register.json`** — structural, evidential, and architectural gaps in HLD
  coverage that Journey 2 cannot resolve by reading the HLD alone.

Three advisory views (human-readable, not canonical):
- **`open_questions.md`** — rendered from ledger: OPEN + ESCALATED questions.
- **`answered_assumptions.md`** — rendered from ledger: ASSUMED questions with
  rationale.
- **`test_strategy.md`** — testability plan per slice, drawn from quality-lens
  output.

One new registry (separate from the helper registry):
- **`hldspec/lens_registry.py`** — inquiry frames. Defines *what* to ask, not *how
  to operate a tool*.

---

## 2. Artifact placement in the source package

| Artifact | AUTHORITATIVE_FILES | REQUIRED_FILES | MIRROR_EXCLUDED | Notes |
|---|---|---|---|---|
| `inquiry_ledger.json` | yes (hashed) | no (migration) | no | Canonical epistemic state |
| `gap_register.json` | yes (hashed) | no (migration) | no | Canonical gap state |
| `open_questions.md` | yes (hashed) | no | yes | Advisory; rendered from ledger |
| `answered_assumptions.md` | yes (hashed) | no | yes | Advisory; rendered from ledger |
| `test_strategy.md` | yes (hashed) | no | yes | Advisory; drawn from quality lens |

`MIRROR_EXCLUDED` follows the same pattern as `helper_recommendations.json`:
advisory guidance for Journey 3 humans, not SpecKit runner content. All five are
excluded from `REQUIRED_FILES` for migration safety — existing packages remain
valid without them.

---

## 3. Question lifecycle states

```
OPEN                  → raised; no answer yet
ANSWERED_FROM_HLD     → resolved by reading HLD content + anchors
ANSWERED_FROM_EVIDENCE → resolved by target repo evidence
ASSUMED               → accepted assumption (human or Journey 2 policy default)
ESCALATED             → requires human decision; blocks PASS until resolved
SUPERSEDED            → replaced by a more precise question (carries pointer)
```

State transitions:
- OPEN → ANSWERED_FROM_HLD / ANSWERED_FROM_EVIDENCE / ASSUMED / ESCALATED /
  SUPERSEDED
- ESCALATED → ANSWERED_FROM_HLD / ANSWERED_FROM_EVIDENCE / ASSUMED (human provides
  the answer)
- No state regresses to OPEN once resolved.

Gate impact:
- Any `ESCALATED` with no `answer` → `blocks_promotion: true` → gate must not PASS
  (same weight as RunSkeptic CONFLICT).
- `OPEN` questions with no slice binding are warnings (ACTION), not blockers.
- `ASSUMED` questions are informational; the ledger records the rationale and the
  gate does not block on them.

---

## 4. Gap types and severity

```
gap_type:
  STRUCTURAL   — HLD section expected by a lens but absent
  EVIDENTIAL   — claim in spec-input has no supporting HLD anchor
  ARCHITECTURAL — open design decision (source-of-truth, interface contract,
                  ownership)
  TESTABILITY  — a slice has no testable observable behavior defined

severity:
  BLOCKER      — gap prevents safe compilation; blocks PASS
  WARNING      — gap is noted; produces ACTION
  NOTE         — informational; neither PASS nor ACTION affected
```

A gap is **resolved** when it receives a `resolution` (human answer or Journey 2
policy fill). `BLOCKER` gaps that remain unresolved block PASS. `WARNING` gaps
return ACTION. `NOTE` gaps do not affect gate state.

---

## 5. Lens registry

A **lens** is an inquiry frame: it defines a domain of questioning, what inputs it
reads, how it generates question candidates, and when it escalates. Lenses are
**separate from helpers**. The helper registry (`hldspec/helper_registry.py`) defines
what a tool can and cannot do. The lens registry (`hldspec/lens_registry.py`) defines
what questions to ask.

### 5.1 Lens types

| Type | Reads | Questions about |
|---|---|---|
| `DOMAIN` | HLD content, user journey sections | User ownership, data invariants, domain rules, who decides what |
| `ARCHITECTURE` | HLD contracts, dependency sections, SoT claims | Source of truth, interface contracts, tech risk, dependency order |
| `QUALITY` | Slice set, quality-gate sections | Testability per slice, observable behavior, quality gates, failure modes |
| `TOOL_HELPER` | `helper_registry` entry, package file list | What evidence a helper needs, what files it reads, what it cannot do |

### 5.2 Lens schema (sketch)

```python
# hldspec/lens_registry.py

LENS_SCHEMA_VERSION = 1

LENS_TYPE_DOMAIN        = "DOMAIN"
LENS_TYPE_ARCHITECTURE  = "ARCHITECTURE"
LENS_TYPE_QUALITY       = "QUALITY"
LENS_TYPE_TOOL_HELPER   = "TOOL_HELPER"

VALID_LENS_TYPES = frozenset({
    LENS_TYPE_DOMAIN, LENS_TYPE_ARCHITECTURE,
    LENS_TYPE_QUALITY, LENS_TYPE_TOOL_HELPER,
})

REQUIRED_LENS_FIELDS = (
    "lens_id",
    "lens_type",
    "display_name",
    "version",
    "questions_about",    # list[str] — topic areas
    "can_answer_from",    # list of: "HLD_CONTENT" | "TARGET_EVIDENCE" | "HUMAN_ONLY"
    "escalates_when",     # str — concrete escalation condition
    "provenance",         # {source: "hldspec_builtin" | "tool:<helper_id>"}
)
```

### 5.3 TOOL_HELPER lens provenance rule

A `TOOL_HELPER` lens must carry `provenance.source = "tool:<helper_id>"` where
`<helper_id>` resolves to a known helper in `helper_registry.build_registry()`.
Unknown `helper_id` → `validate_lens_registry()` error. This is the **only** place
the lens registry references the helper registry — to verify the tool exists. Helper
capabilities are never duplicated into the lens.

### 5.4 What lenses do NOT carry

- Authority levels (those are in `helper_registry`)
- Lifecycle states (lenses are not onboarded through the Bootstrap)
- Negative capability fields (`cannot_do`, `forbidden_actions`, etc.)
- Selected helper (that is `.hldspec/helper_selection.json`, Journey 3)

A tool/skill may contribute both a helper entry (capabilities) and a lens (inquiry
frame). They are separate registries with separate concerns.

---

## 6. Schema sketches

### `inquiry_ledger.json`

```json
{
  "schema_version": 1,
  "generated_at": "<iso8601>",
  "source_package_sha256": "<sha of source_manifest.json>",
  "questions": [
    {
      "question_id": "Q-001",
      "text": "Who owns the auth token — is it user-scoped or session-scoped?",
      "status": "ESCALATED",
      "lens_id": "architecture",
      "hld_anchors": ["HLD-003", "HLD-007"],
      "binds_to_slices": ["slice-auth-boundary"],
      "can_answer_from": ["HUMAN_ONLY"],
      "answer": null,
      "assumption_rationale": null,
      "escalation_reason": "HLD-003 and HLD-007 make contradictory ownership claims",
      "superseded_by": null
    }
  ],
  "gate_impact": {
    "escalated_unresolved": 1,
    "open_unbound": 0,
    "blocks_promotion": true
  }
}
```

### `gap_register.json`

```json
{
  "schema_version": 1,
  "generated_at": "<iso8601>",
  "gaps": [
    {
      "gap_id": "GAP-001",
      "gap_type": "STRUCTURAL",
      "severity": "BLOCKER",
      "lens_id": "quality",
      "description": "No error-handling strategy section; slice-error-handling has no observable failure behavior",
      "hld_anchors": [],
      "binds_to_slices": ["slice-error-handling"],
      "resolution_status": "OPEN",
      "resolution": null
    }
  ],
  "gate_impact": {
    "blocker_unresolved": 1,
    "warning_unresolved": 0,
    "blocks_promotion": true
  }
}
```

---

## 7. Binding model

Every question and gap binds to three anchor types:

| Binding | What it means | Integrity rule |
|---|---|---|
| `hld_anchors` | HLD sections the question is about | Must exist in `hld_reference_map.json`; unknown anchor → build error (same rule as spec-input claims) |
| `binds_to_slices` | Implementation slices blocked or affected | Must exist in `implementation_slices.json`; unknown slice → build warning |
| `lens_id` | Which lens generated the question/gap | Must exist in `lens_registry`; unknown lens → build error |
| `can_answer_from` | Resolution path | `HLD_CONTENT` / `TARGET_EVIDENCE` / `HUMAN_ONLY` |

**Slice-blocking rule:** a slice whose `slice_id` appears in any unresolved
`ESCALATED` question's `binds_to_slices` is not safe to deliver. Journey 3 reads
this when deciding which slices are READY.

**Evidence refs:** `ANSWERED_FROM_EVIDENCE` questions carry an `evidence_refs`
list — pointers to target repo files or commit SHAs that supplied the answer. Must
be non-empty for status `ANSWERED_FROM_EVIDENCE`.

---

## 8. Gate integration

The inquiry/gap artifacts slot into the existing `SOURCE_PACKAGE_APPROVAL_GATE`
as additional blocking conditions:

| Condition | Gate effect |
|---|---|
| `inquiry_ledger.gate_impact.blocks_promotion == true` | → BLOCKED |
| `gap_register.gate_impact.blocker_unresolved > 0` | → BLOCKED |
| `gap_register.gate_impact.warning_unresolved > 0` | → ACTION |
| `inquiry_ledger.gate_impact.open_unbound > 0` | → ACTION |
| All above conditions clear | → does not block (other gate conditions still apply) |

Ledger and register absent (legacy package) → gate ignores them (files optional).
Gate does not retroactively fail old packages.

---

## 9. Separation of concerns

| Registry / Artifact | Where | Defines |
|---|---|---|
| Helper capabilities | `hldspec/helper_registry.py` | What a tool CAN and CANNOT do, authority, lifecycle |
| Inquiry lenses | `hldspec/lens_registry.py` | What QUESTIONS to raise, from what domain |
| Inquiry ledger | `source_package/inquiry_ledger.json` | Per-package question instances + status |
| Gap register | `source_package/gap_register.json` | Per-package HLD coverage gaps |
| Helper recommendations | `source_package/helper_recommendations.json` | Advisory helper selection for this package |
| Helper selection | `.hldspec/helper_selection.json` | Journey 3 target/human decision — **future** |

A `TOOL_HELPER` lens may reference a `helper_id` only to verify the helper exists.
It does not copy, restate, or extend the helper's capabilities. The helper's
`required_package_files` and `required_target_evidence` in `helper_registry.py` are
authoritative — the `TOOL_HELPER` lens generates questions *about* that requirement
set; it does not redefine it.

---

## 10. Invariants

1. `inquiry_ledger.json` and `gap_register.json` are AUTHORITATIVE — hashed in the
   manifest; no question or gap may be silently dropped between builds.
2. A question's `hld_anchors` must reference only anchors present in
   `hld_reference_map.json` — same integrity rule as spec-input claims.
3. `ESCALATED` questions with no `answer` → `blocks_promotion: true` → gate must
   not PASS.
4. `BLOCKER` gaps with `resolution_status == "OPEN"` → `blocks_promotion: true`.
5. `open_questions.md`, `answered_assumptions.md`, and `test_strategy.md` are
   generated views — never authoritative. If they conflict with the ledger JSON, the
   JSON wins.
6. `hldspec/lens_registry.py` carries no authority levels, lifecycle states, or
   negative capability fields. Separation is structural, not just conventional.
7. A `TOOL_HELPER` lens `provenance.source = "tool:<helper_id>"` must resolve to a
   known `helper_id` in `helper_registry.build_registry()`.
8. `lens_id` is recorded on every question and gap — lens drift is detectable by
   comparing the ledger's `lens_id` values against the current `lens_registry`.
9. The inquiry ledger does not record `selected_helper` — that is
   `.hldspec/helper_selection.json` (Journey 3, future).
10. Journey 2 never auto-resolves `ESCALATED` questions — only a human can provide
    the `answer` that transitions state.

---

## 11. Migration / backward-compatibility

- All five artifacts are in `AUTHORITATIVE_FILES` but not `REQUIRED_FILES` —
  existing packages pass the gate without them.
- When the files are present, they are hashed and validated. When absent, the gate
  ignores their blocking conditions.
- `hldspec/lens_registry.py` is a new internal module with no effect on existing
  source packages until it is wired into the compilation path (a future slice).
- No existing invariants are touched. `MIRROR_FILES` construction already uses
  `_MIRROR_EXCLUDED` — adding the three advisory files follows the established
  pattern.

---

## 12. RunSkeptic questions for this contract

- **CH (inversion):** If an ESCALATED question is silently dropped between builds,
  does the manifest hash catch it? (It should — the ledger is AUTHORITATIVE.)
- **OM (parsimony):** Does every lens earn its place — does it produce questions that
  cannot be derived from the three other lenses?
- **FE (mechanism):** Can a reader trace from a specific gap back to the HLD anchor
  and the lens that raised it?
- **PO (refutation):** Show a package the gate would PASS despite an unresolved
  BLOCKER gap. Can that happen? (It should not — `blocker_unresolved > 0` →
  BLOCKED.)
- **KT (universalizability):** Are the five question states sufficient for every
  HLD, including one where every question resolves from the HLD itself (all
  `ANSWERED_FROM_HLD`, no ESCALATED)?
- **SH (tradeoff):** Two canonical JSON files (`inquiry_ledger` + `gap_register`)
  vs. one combined file — is the split earning its complexity, or would a single
  artifact suffice?

---

## 13. Future tests (to add when implemented)

1. `test_ledger_escalated_blocks_pass` — ESCALATED unresolved → gate BLOCKED
2. `test_ledger_all_resolved_clears_gate` — all ANSWERED/ASSUMED → ledger does not
   block
3. `test_gap_blocker_blocks_pass` — BLOCKER gap OPEN → gate BLOCKED
4. `test_gap_warning_returns_action` — WARNING gap → ACTION, not BLOCKED
5. `test_question_anchor_integrity` — question referencing unknown HLD anchor →
   build error
6. `test_lens_has_no_authority_levels` — `validate_lens` rejects `authority_levels`
   field
7. `test_lens_has_no_lifecycle_state` — `validate_lens` rejects `lifecycle_state`
   field
8. `test_tool_helper_lens_provenance_resolves` — lens with `tool:speckit` validates
   against registry; `tool:unknown` fails
9. `test_open_questions_md_not_in_mirror` — `open_questions.md` in `_MIRROR_EXCLUDED`
10. `test_inquiry_ledger_in_authoritative_not_required` — `inquiry_ledger.json` in
    `AUTHORITATIVE_FILES`, absent from `REQUIRED_FILES`
11. `test_gap_register_in_authoritative_not_required` — same for `gap_register.json`
12. `test_ledger_sha256_provenance` — `source_package_sha256` changes when package
    changes
13. `test_answered_from_evidence_has_evidence_refs` — `ANSWERED_FROM_EVIDENCE` with
    empty `evidence_refs` → validation error
14. `test_lens_registry_validates_clean` — `validate_lens_registry(build_lens_registry())`
    returns empty errors

---

## 14. Non-goals

- The lens registry does **not** automatically generate questions at runtime —
  that is a future compilation slice.
- The inquiry ledger does **not** replace RunSkeptic — RunSkeptic remains a
  separate quality gate with its own six-lens framework.
- `open_questions.md` and `answered_assumptions.md` are **not** sources of truth —
  they are rendered views; the ledger JSON is authoritative.
- The inquiry ledger does **not** track implementation progress — that is the
  invocation queue + run-card state.
- The lens registry does **not** select which helper to use — that is
  `helper_selection.json` (Journey 3, future).
- Journey 2 does **not** auto-resolve `ESCALATED` questions by inference — human
  answer is required.
- This contract does **not** define how lenses are invoked or scheduled — the
  compilation pipeline order is a future runtime slice.
- `NextActionPacket` is not introduced here — it belongs to the helper runtime
  (Journey 3 future).

---

## 15. Vocabulary additions (to `JOURNEY2_PACKAGE_CONTRACT.md` §13)

| New term | Artifact |
|---|---|
| inquiry ledger | `source_package/inquiry_ledger.json` |
| gap register | `source_package/gap_register.json` |
| open questions view | `source_package/open_questions.md` |
| answered assumptions view | `source_package/answered_assumptions.md` |
| test strategy view | `source_package/test_strategy.md` |
| inquiry lens / lens registry | `hldspec/lens_registry.py` |
| domain / architecture / quality / tool-helper lens | lens types in lens registry |
| question lifecycle state | OPEN / ANSWERED_FROM_HLD / ANSWERED_FROM_EVIDENCE / ASSUMED / ESCALATED / SUPERSEDED |
| gap type | STRUCTURAL / EVIDENTIAL / ARCHITECTURAL / TESTABILITY |
| gap severity | BLOCKER / WARNING / NOTE |
