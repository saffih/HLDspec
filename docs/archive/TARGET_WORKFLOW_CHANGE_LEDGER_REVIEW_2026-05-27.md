# Review — Ordinary target-repo workflow & provisional source-truth deltas

Read-only review (RunSkeptic-informed) of whether the current HLDspec control plane
supports the ordinary target-repo workflow:

> User is in the target repo and says: "I want X. Make it happen."

Goal to preserve: **only the controller promotes source truth**, while still letting
target agents keep *provisional* source-truth records during normal work.

Final category: **CONFLICT** — the design does not yet support this; it needs a new
"change ledger" capability with four human-owned design choices (surfaced below).

---

## RunSkeptic Receipt

- **Source read:** `/Users/saffi/code/skeptic/skeptic.md`, sha256
  `c5f60f48a09660e63fb09cf2a464185f928608ba5823fa7284aff6c56e9959bb` (unchanged).
- **Permission mode:** read-only. No code edited for this review.
- **DONE statement:** "Answer the 9 workflow pressure-test questions with current
  state / gap / proposal; decide whether the change-ledger capability is buildable now
  or needs human design decisions first."
- **Major steps:** GATE, FUNDAMENTAL SCAN, MAP, STABILIZE, EVIDENCE, DECIDE.
- **Thinkers considered:** CH, OM, FE, PO, KT, SH.
- **Evidence used:** committed control plane (`session_control.py`, `gate_validator.py`,
  `hld_source_package.py`, `hld_marking.py`, `single_spec_input.py`, Slice 5
  `hld_diff.py`/`stale_check.py`); canonical doc §2/§12; AGENTS.md ownership rules.
- **Decision path:** GATE → "real capability gap, multiple valid designs, ownership
  choice involved" → CONFLICT (escalate design choices), with a concrete proposal per
  question.
- **Final output category:** CONFLICT (human design decisions required).

---

## The core gap (FUNDAMENTAL SCAN)

The control plane is built for **formal HLDspec→SpecKit phases**: HLD is shaped, a
source package is approved, the controller gates each phase. It assumes source truth
is settled *before* execution.

The ordinary workflow inverts this: code changes **first** ("make X happen"), and the
question is whether source truth catches up. The current design has **no place** for a
target agent to record "I changed behavior X; here is the provisional source-truth
delta." Today the only writable source-of-truth area is `.hldspec/source_package/`,
which is controller-owned and must not be written by bounded agents. So a target agent
either (a) can't record the delta at all, or (b) would have to violate the ownership
rule. That is the conflict.

**PO (failure signal):** nothing currently blocks "code changed, HLD unchanged." Slice 5
detects *HLD-side* drift (HLD changed → derived artifacts stale). The *code-side* drift
(code changed → HLD now lies) is undetected and ungated. This is the sharpest gap.

---

## Pressure-test questions: current state / gap / proposal

**Q1. Where does the target agent record a normal user change request?**
- Current: nowhere. No artifact captures "user asked for X."
- Proposal: a change ledger entry per request, in a writable area (see Q6).

**Q2. Where is the provisional source-truth delta kept for exploratory/POC work?**
- Current: nowhere; canonical source package is the only source-truth store and is
  controller-owned.
- Proposal: `changes/<change-id>/source_delta.md` (provisional, agent-writable),
  distinct from the canonical package. Promoted into the package only by the controller.

**Q3. Does the target repo get generated AGENTS.md telling agents to update deltas?**
- Current: `target_agents.py` is not yet built; no generated target AGENTS.md instructs
  delta recording.
- Proposal: generate target `AGENTS.md` with a rule: "if you change app behavior/arch/
  API/data/UI/ownership, record a provisional delta under `changes/<change-id>/` before
  reporting done; never edit `.hldspec/source_package/**`."

**Q4. Is there a lightweight change ledger (ask → interpretation → diff → impact →
evidence → status)?**
- Current: no. `phase_report.json` is execution-phase-shaped, not change-shaped.
- Proposal: `changes/<change-id>/change.json` with exactly those fields + status
  `PROVISIONAL | ACCEPTED | REVISED | REJECTED` (only controller sets non-PROVISIONAL).

**Q5. Are target agents forbidden from all of `.hldspec/source_package/**`? If so how do
they record deltas?**
- Current: yes — packets forbid `.specify/**` and treat the source package as read-only
  for runner/consultant. Correct for canonical truth; but it leaves no record path.
- Proposal: keep the package read-only for agents; give them a **separate** writable
  ledger area (Q6). Ownership rule intact: agents write *provisional* deltas, controller
  promotes.

**Q6. Can we protect canonical source truth while allowing a narrow writable area like
`changes/<change-id>/`?**
- Current: not defined.
- Proposal (the key ownership choice — see Decision 1): a writable ledger root that is
  **not** the canonical package and is **not** mirrored to `.specify/`. Candidates:
  `target/.hldspec/changes/` (HLDspec-owned control area, off the canonical package) or
  `target/changes/` (target-repo-owned, simplest permissions).

**Q7. Do phase reports require behavior/source-truth impact fields?**
- Current: no. `PHASE_REPORT_REQUIRED_KEYS` = phase/actor/validation/runskeptic/
  consultant/next_safe_action only.
- Proposal (Decision 3): add `behavior_impact` and `source_truth_impact` (+ `change_id`)
  required keys for runner phases that touch the target.

**Q8. Does the dirty-tree gate distinguish expected change files from unrelated work?**
- Current: no — `target_dirty_files` blocks on *any* dirty file (conservative-correct).
- Proposal: once the ledger exists, allow paths under the writable ledger area and the
  change's declared files; still block genuinely unrelated dirt.

**Q9. What blocks "code changed, but no source-truth delta was recorded"?**
- Current: **nothing.** This is the headline gap.
- Proposal (Decision 2): an audit that compares the change's git diff against a recorded
  delta; if code changed and no `source_truth_impact`/delta exists, classify BLOCK at the
  relevant gate.

---

## Decisions required (human-owned) — surfaced via AskUserQuestion

1. **Writable ledger location** — `target/.hldspec/changes/` (HLDspec control area, not
   mirrored) vs `target/changes/` (target-owned) vs other.
2. **Enforcement of "code changed, no delta"** — runner self-declares in phase report +
   consultant audits (review-time) vs a basepack/controller git-diff audit at gate time
   vs not enforced yet (detect-only this slice).
3. **Phase-report extension** — add `behavior_impact` / `source_truth_impact` /
   `change_id` now vs defer.
4. **Build scope of Slice 6** — full ledger (area + schema + AGENTS.md + enforcement +
   dirty-tree allowance) vs minimal (writable area + ledger schema + AGENTS.md guidance,
   enforcement detect-only) vs design-doc-only for now.

## Invariant to preserve across all options

Provisional deltas are **agent-writable**; promotion into the canonical
`.hldspec/source_package/` remains **controller-only** (MODEL_SMART / human). The ledger
never becomes a second source of truth — it is a staging record the controller reconciles.
