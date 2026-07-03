# Flow SDD-Ready Gate — v2 HLD Assessment

Date: 2026-07-03

Status: **RATIFIED** — owner sign-off recorded 2026-07-04
(`FLOW_SDD_GATE_V2_OWNER_SIGNOFF`).

## Purpose

Fresh SDD-ready gate assessment against the current Flow HLD v2, following:

- PR #122: gate re-run recorded BLOCKED with six drift items.
- PR #123: drift disposition ratified — all six items classified, owner
  decisions recorded for items 2/3.
- Finding: Flow HLD v2 (promoted in Flow PR #13) already incorporates all
  seven patch items. No additional target HLD patch was needed.

This report performs the formal §5/§6/§9/§10 gate assessment that PR #122 did
not do against v2 (it referenced the prior readiness report's BLOCKED verdict
without re-counting against the updated HLD text).

- This does not modify `/Users/saffi/code/flow`.
- This does not invoke SpecKit.
- This does not start Journey 2 or Journey 3.
- This does not create backlog or implementation scope.
- This does not close J0-12 globally.

## Evidence reviewed

- `docs/JOURNEY1_SDD_READY_GATE.md` (the gate contract)
- `docs/flow_journey1_hld_hardening/flow-drift-disposition.md` (PR #123)
- `docs/flow_journey1_hld_hardening/flow-hld-hardening-owner-decisions.md`
  (PR #120)
- `docs/flow_journey1_hld_hardening/flow-sdd-ready-gate-rerun.md` (PR #122)
- `docs/TARGET_SNAPSHOT_HASH_PROVENANCE_FIX.md` (PR #121)
- Flow target files: `README.md`, `HLD.md`, `core.md`, `flow.py`,
  `test_flow.py`

## Target snapshot proof

Target root: `/Users/saffi/code/flow`

| Relative path | SHA-256 | Changed since PR #122? |
|---|---|---|
| `README.md` | `2595a671541a4efd4562884d07922c0b297ad105dfafe56d569f755895409943` | no |
| `HLD.md` | `3c376ae9917b05d09d71fd73037b41a800eecbe51eaa5167481f1db11cf7e5d0` | no |
| `core.md` | `3b279dc51456d9c41e58daf8999825acf17f5fa51f7ffb58caa50c7b98a41e21` | no |
| `flow.py` | `613c7078ba2b648379460bfdc7794b60ecdcce494a6bd669213d6417d43d700f` | no |
| `test_flow.py` | `5c41b72ba1a8543ae4aa21bc70c92d482400a43845dbb76f1522351f2b360340` | no |

All hashes match PR #122. No target bytes changed. Pre-existing untracked:
`.hldspec-run.json`, `.hldspec-runs/`.

## Flow test result

```text
66 passed
```

Run with `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider`.

## HLDspec test result

```text
2396 passed (tests_v2/)
138 passed (Journey 0 specific tests)
```

## §6 Required metadata — per-section audit

17 sections. All have HLD-ID, HLD-ROLE, HLD-STATUS, HLD-RISK, HLD-SPECS,
HLD-RESOURCES.

| Section | Risk | HLD-SPECS | HLD-VERIFY | Item status |
|---|---|---|---|---|
| HLD-001 | MEDIUM | provisional (with revisit trigger) | n/a | provisional |
| HLD-002 | LOW | provisional (with revisit trigger) | n/a | provisional |
| HLD-003 | HIGH | constitution | present, non-TBD | baked |
| HLD-004 | HIGH | constitution | present, non-TBD | baked |
| HLD-005 | HIGH | constitution | present, non-TBD | baked |
| HLD-006 | MEDIUM | provisional (with revisit trigger) | n/a | provisional |
| HLD-007 | MEDIUM | constitution | present, non-TBD | baked |
| HLD-008 | HIGH | constitution | present, non-TBD | baked |
| HLD-009 | HIGH | constitution | present, non-TBD | baked |
| HLD-010 | HIGH | constitution | present, non-TBD | baked |
| HLD-011 | LOW | provisional (with revisit trigger) | n/a | provisional |
| HLD-012 | LOW | provisional (with revisit trigger) | n/a | provisional |
| HLD-013 | HIGH | constitution | present, non-TBD | baked |
| HLD-014 | HIGH | constitution | present, non-TBD | baked |
| HLD-015 | HIGH | constitution | present, non-TBD | baked |
| HLD-016 | HIGH | constitution | present, non-TBD | baked |
| HLD-017 | LOW | provisional (with revisit trigger) | n/a | provisional |

All 9 HIGH-risk sections have non-TBD HLD-VERIFY. No raw `TBD` anywhere.

## §6 Required HLD contents

- Purpose/scope: HLD-001 ✓
- Non-goals/out-of-scope: HLD-011 (boundary rule) ✓
- Requirements/feature candidates: HLD-017 ✓
- Architecture/boundaries: HLD-003/004/005/008/009/010/013/014/015/016 ✓
- Constraints and risks: HLD-RISK stated on all 17 sections ✓

## §5 SDD-ready criteria

1. **Bounded**: HLD-011 states the boundary rule; HLD-017 separates committed
   design from candidates from implementation status. ✓
2. **Coherent**: No CONFLICTS_WITH references. The two contradictions from
   the readiness report (escalation concurrency, exclusion list) are resolved
   in the v2 text. ✓
3. **Sourced**: All HIGH-risk sections carry HLD-RATIONALE with explicit
   reason kinds. ✓
4. **Decomposable**: Component boundaries clear (CLI → durable store →
   projection; tasks/batons/reports as distinct layers). ✓
5. **Evidence-anchored**: All HIGH-risk sections have non-TBD HLD-VERIFY. The
   6 provisional sections have explicit revisit triggers (§8 acceptable). ✓

## §9 Blocker ambiguity check

- **Unsourced claims**: none found.
- **Unresolved contradiction**: none found. Old contradictions (escalation
  concurrency per DECLARED-009, exclusion list per DECLARED-010) resolved in
  v2 HLD text.
- **High-risk without evidence**: all 9 HIGH-risk sections have non-TBD
  HLD-VERIFY. ✓
- **Undrawable boundary**: component boundaries are clear. ✓
- **Human-owned decision pending**: all 5 owner decisions (PR #120) applied.
  Items 2/3 drift decisions (PR #123) applied — HLD-017 records the gap
  truthfully. ✓

No §9 blockers found.

## §8 Allowed ambiguity

The 6 provisional HLD-SPECS fields (HLD-001, HLD-002, HLD-006, HLD-011,
HLD-012, HLD-017) each carry:

- Status: `provisional`
- Revisit trigger: "assign when the first spec citing this section is drafted
  — revisit at the next SDD-gate assessment"

Per §8, provisional choices with explicit revisit triggers produce ACTION at
most, not BLOCKED. These are genuine "no spec drafted yet" — not disguised
blockers.

## Formal counts

```
unresolved = 0
provisional = 6
```

## Drift items (PR #122/123)

All six drift items from PR #122 were classified in PR #123 as non-blocking:

- Items 1/4/5/6: implementation gaps, non-blocking per §5.
- Items 2/3: HLD overstatement resolved — HLD-017 centralized gap-tracking
  distinguishes design intent from implementation status (owner decisions
  ratified).

The v2 HLD explicitly states (header): "This document states the target
design. The current runtime implements a subset of it; HLD-017 records the
design-vs-implementation gap." This satisfies the owner's general rule: no
overstated current-behavior claims.

## Verdict: ACTION

Per §10: `unresolved == 0` and `provisional > 0` →
**`HLD_READY_WITH_ACTIONS`** (ACTION).

The Flow HLD v2 is SDD-ready with actions. The 6 provisional HLD-SPECS
fields are the listed action items — each requires spec assignment when the
first spec citing that section is drafted.

This is the first non-BLOCKED verdict for Flow.

## Promotion rule (§10)

ACTION promotes to Journey 2 only after the human **explicitly accepts** the
listed risks:

**Risk: 6 sections have no assigned spec intent.**

- HLD-001 (purpose, MEDIUM): no spec yet.
- HLD-002 (vocabulary, LOW): no spec yet.
- HLD-006 (escalation triggers, MEDIUM): no spec yet.
- HLD-011 (scope boundary, LOW): no spec yet.
- HLD-012 (technology, LOW): no spec yet.
- HLD-017 (requirements/candidates, LOW): no spec yet.

Revisit trigger on all: assign at the next SDD-gate assessment or when the
first spec citing the section is drafted.

**Acceptance means:** Journey 2 may decompose features using the 11
constitution-backed sections; it flags or defers decomposition for the 6
provisional sections until specs exist. The revisit trigger ensures specs are
assigned when they exist, not before.

## RunSkeptic

Source: `https://raw.githubusercontent.com/saffih/skeptic/main/skeptic.md`
Source SHA-256: `9ef639b607bd2cf7e5094f6af494872ef3dd029c1cd448184bf40b64c5ef7acd`

**CH (inversion):** If this HLD passes to Journey 2, worst downstream outcome
is Journey 2 tries to decompose features for the 6 provisional sections and
has no spec intent to anchor on. Bounded: the revisit trigger flags these
during decomposition; Journey 2 asks rather than guesses (gate §12: "must not
invent product truth").

**OM (parsimony):** The 6 provisional fields don't block decomposition of the
11 constitution-backed sections. They are lower-risk (MEDIUM or LOW) where
SPECS is genuinely TBD because no spec exists yet. The gate surfaces real
unknowns, not ceremony.

**FE (mechanism):** Verdict path is transparent: 17 sections × metadata →
unresolved (0) + provisional (6) → ACTION. The reader can verify by checking
the 6 "provisional" SPECS fields against the audit table above.

**PO (refutation):** Could a bad HLD pass silently? §17 known limit: the
heuristic misses semantic contradictions not declared as CONFLICTS_WITH. No
undeclared contradictions were observed in this review, but the caveat holds —
human judgment remains the backstop for structural completeness.

**KT (universalizability):** Applied to any HLD that hasn't drafted specs for
lower-risk sections, this gate produces ACTION with revisit triggers. That is
appropriate — specs are assigned when they exist, not manufactured.

**SH (tradeoff):** The gate resolves flexibility-vs-quality: design intent is
authoritative (sections state the target), implementation status is truthful
(HLD-017), spec assignment is deferred until specs exist (provisional +
trigger). No false precision, no false readiness.

RunSkeptic verdict: **HANDLED / ACTION is the honest verdict.**

## HLDspec checks run

- `git diff --check`: clean
- `git diff --stat` / `git diff --name-only`: disposition update only
- Hidden/bidi scan on changed HLDspec files: clean
- `python3 -m pytest tests_v2/`: 2396 passed
- `python3 -m pytest tests_v2/test_journey0_*.py`: 138 passed
- Flow tests (target, no mutation): 66 passed
- Target snapshot hashes: all match PR #122, no bytes changed

## Owner sign-off

Date: 2026-07-04.
Source: owner direction via session handoff.

Two judgment calls required before the ACTION verdict is authoritative:

### 1. Session enforcement (item 2) — HLD-017 gap tracking sufficient?

Owner decision: option (b) — the HLD was overstated as current working
behavior. The v2 HLD satisfies this: HLD-017 states "optional session naming
(not yet the mandatory named sessions of HLD-009/010)"; the document header
declares "this document states the target design." No additional HLD patch
needed. Non-blocking implementation gap.

### 2. Explicit reclaim (item 3) — HLD-017 gap tracking sufficient?

Owner decision: option (b) — the HLD was overstated as current working
behavior. The v2 HLD satisfies this: HLD-017 states "lease-based reclaim with
escalate-on-repeat (not yet the see-and-act reclaim verb of HLD-014)." No
additional HLD patch needed. Non-blocking implementation gap.

Both verified against `/Users/saffi/code/flow/HLD.md` (SHA-256:
`3c376ae9917b05d09d71fd73037b41a800eecbe51eaa5167481f1db11cf7e5d0`).

## Forbidden conclusions

This report does not authorize:

- Mutating `/Users/saffi/code/flow`
- Invoking SpecKit
- Command wiring
- Journey 2 or Journey 3 start (even on ACTION — requires explicit human
  risk acceptance first)
- HLD writing
- Backlog or implementation scope
- Global J0-12 closure
- Treating candidate capabilities (HLD-017) as implemented commitments

## Next action

The human/project owner reviews the 6 provisional items and either:

1. **Accepts the risk** (records risk acceptance for each provisional item
   with revisit trigger) → verdict promotes to PASS equivalent for Journey 2.
2. **Assigns spec intent** to one or more provisional sections → re-run
   produces a lower provisional count.
3. **Neither** → verdict stays ACTION; Journey 2 does not start.

Do not start Journey 2 or Journey 3 automatically.
