# Flow Journey 1 Planning Justification

**Status:** planning justification only. This doc records the human-reviewable
basis for considering a Journey 1 (HLD authoring/hardening) planning effort for
the `flow` target. It authorizes nothing by itself.

- This does not start Journey 1 execution.
- This does not authorize SpecKit.
- This does not authorize command wiring.
- This does not write HLD content.
- This does not create backlog or implementation scope.
- This does not mutate `/Users/saffi/code/flow`.
- Declared evidence is usable for planning but still requires human review
  before authoritative HLD writing.
- PASS means Journey 1 planning consideration, not automatic HLD generation.

Backlog item J0-17 ("Journey 1 start from Journey 0") remains **BLOCKED** in
`docs/HLDSPEC_DEVELOPMENT_BACKLOG.md`. This doc does not lift it.

## Purpose

Answer one question: is a Journey 1 planning effort for `flow` justified by the
Journey 0 real-target dry-run evidence (RT-1, RT-2)? If yes, bound what that
planning may use and what it must not do.

## Inputs reviewed

- `docs/journey0_real_target_dry_runs/flow-journey0-dry-run.md` (RT-1)
- `docs/journey0_real_target_dry_runs/flow-journey0-declared-evidence-dry-run.md` (RT-2)
- `docs/THREE_JOURNEYS.md` (Journey 1 definition and boundary; §8 Journey 0 pointer)
- `docs/JOURNEY0_SCHEMA_AND_WIRING_PLAN.md` (PASS semantics; stabilization table)
- `docs/HLDSPEC_DEVELOPMENT_BACKLOG.md` (J0-12, J0-14 … J0-17 blockers)

No target-repo files were read for this doc. No new evidence was collected.

## RT-1 summary

- Target `/Users/saffi/code/flow`; allowed paths `README.md`, `HLD.md`, `core.md`.
- Declared product-surface evidence intentionally empty.
- Verdict: **ACTION** — generic file evidence (doc_file, hld_fragment) cannot
  produce PASS alone; 0/5 product-surface categories populated, 1 unknown.
- No-mutation proof clean (SHA-256 before/after match on all 3 files).

## RT-2 summary

- Same target and path set; target hashes unchanged since RT-1.
- 10 user-approved declared product-surface evidence items (2 per category:
  capability, actor, input/output, workflow, limit), DECLARED-001…010.
- Verdict: **PASS** — 5/5 categories populated, 0 unknowns; all 13 evidence
  items accepted; no product decisions triggered; no blocking items.
- No-mutation proof clean; hashes match RT-1.

## What Journey 0 proved

1. Generic file evidence alone does not produce PASS (RT-1).
2. Declared product-surface evidence composes correctly with structural
   evidence and is what moved the verdict from ACTION to PASS (RT-2).
3. The draftability gate responds to explicit product-surface coverage, not
   file existence.
4. The pipeline ran against a real target twice with zero mutation.
5. RT-2's PASS explicitly means evidence sufficiency for Journey 1
   consideration — neither report authorizes Journey 1 execution.

## Evidence usable for Journey 1 planning

All 10 declared items (DECLARED-001…010, as tabulated in the RT-2 report) are
usable for **planning scope and structure**: they name the capability areas,
actors, input/output surfaces, workflows, and limits a `flow` HLD would need to
cover, and RT-2's HLD update plan already maps them to five candidate sections.
Planning may cite them by DECLARED id and RT-2 provenance column only.

## Evidence requiring human confirmation before HLD writing

All 10 items require human accuracy review before any authoritative HLD
writing (per the RT-2 provenance caveat). Two need explicit attention:

- **DECLARED-005** (CLI in; SQLite state + markdown projections out): names
  implementation technology (SQLite). Human must confirm whether this is
  product surface or an implementation detail before it anchors HLD content.
- **DECLARED-009** (one open escalation per task): a structural invariant
  interpreted from HLD-005. Human must confirm it is current product intent,
  not stale design residue.

No item is classified out of scope; none may be expanded, merged, or
reinterpreted into new product claims during planning.

## Provenance caveat

Declared evidence is user-approved but **not automatically validated as
product truth**. It was drafted by reading the three allowed target files and
approved by a human for dry-run use, not ratified as authoritative product
definition. Additionally, the full Journey 0 provenance model is still open
(backlog J0-12: PROVENANCE_OPEN). Any Journey 1 planning output must carry
this caveat forward verbatim, and HLD writing must not begin until the
declared items are human-confirmed as product truth.

## What Journey 1 planning may do

- Scope a Journey 1 HLD-hardening plan for `flow` using only the RT-2 accepted
  evidence refs (COLLECTED-001…003, DECLARED-001…010).
- Use the RT-2 HLD update-plan section mapping as the candidate structure.
- Define the human confirmation checklist for the 10 declared items.
- Define PASS/ACTION/BLOCKED expectations for the flow HLD per
  `docs/JOURNEY1_SDD_READY_GATE.md`.
- Produce planning documents in HLDspec `docs/` only.

## What remains forbidden

- Journey 1 execution (HLD authoring/hardening) — J0-17 is BLOCKED.
- Writing or editing any HLD content, in HLDspec or in the target.
- SpecKit invocation; Journey 2 packaging; Journey 3 helper handoff.
- Command-surface wiring of Journey 0 or Journey 1 (J0-16 DO_NOT_WIRE).
- Any mutation of `/Users/saffi/code/flow` or reads outside the three allowed
  paths.
- Backlog or implementation scope creation for `flow`.
- Treating declared evidence as verified product truth.

## Stop conditions

Stop and return to human review if any of these occur during planning:

- A declared evidence item is contradicted, reinterpreted, or expanded.
- Planning output starts to contain HLD section prose (that is HLD writing).
- Any step requires reading new target paths or re-running against the target.
- Any step requires command wiring, SpecKit, or target mutation.
- The provenance caveat would be weakened or dropped.

## Recommended next action

Journey 1 **planning is justified** on the RT-1/RT-2 evidence, within the
bounds above. Next: prepare a separate, human-approved Journey 1
planning-scope prompt that includes the 10-item human confirmation checklist.
Do not auto-start Journey 1 execution; J0-17 remains BLOCKED until human and
project approval after blocker and stabilization review.
