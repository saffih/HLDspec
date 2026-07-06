# Flow — C1 / C2 / G1 Owner-Decision Record (pre-`/speckit.implement`)

Feature: `025-store-transaction-foundation` (Flow target repo)
Date: 2026-07-06 (decision slice)
Status: **RECORDED** — C1 phasing decided, C2 header fixed (minimal), G1 T011 extension applied, analyze phase evidence accepted. `/speckit.implement` was NOT run. Update 2026-07-06: Flow decision PR #20 **MERGED** (see Changes / PRs).

---

## Authorization

Owner-authorized clean-room decision slice (TOUGHNESS HIGH). Scope: verify Flow PR #19
and HLDspec PR #139 merged, re-derive analyze findings C1/C2/G1 from current evidence,
record owner decisions for C1/C2/G1 and stdout-only analyze phase evidence, optionally
apply a tiny G1 `tasks.md` task-line extension and a tiny C2 constitution header/status
fix (only if mechanically clear and authority-unambiguous), open PRs.
Explicitly NOT authorized: any SpecKit command (specify/clarify/plan/tasks/analyze/
implement), implementation, command wiring, source-package mutation, product/runtime
mutation, broad constitution rewrite, broad CLI/session enforcement, `flow.py`/
`test_flow.py`/CLI-parser changes, driver changes for stdout-only analyze evidence,
ignored `CLAUDE.md` or `.gitignore` mutation, merging any PR.

## Clean-room proof

- Prior chat context used as evidence: no
- Previous agent memory used as evidence: no
- Auto-injected memory/context used as evidence: no
- Pasted receipts used as evidence: no
- Handoff summaries used as evidence: no
- Claims treated as verification targets, not proof: yes
- Evidence source limited to current repos/GitHub/files/commands/tests/fresh skeptic.md: yes
- Any unverified load-bearing claim identified: no

Executed by lead + true subagent workers A–I (merge/state, C1 phasing, C2 constitution
header, G1 FR-006, analyze evidence, mutation boundary, patch/record verification,
tests/bidi/RunSkeptic, PR verification), each producing a bounded receipt. Minimal
mutations were lead-applied from worker-verified evidence and independently
scope-verified (Worker G).

## Verified preconditions (re-derived)

- Flow PR #19: MERGED (2026-07-06T06:19:10Z), head `dcce6712e49e30faac1014a8ec698eff43970472`,
  merge commit `90113e0b06d6680252d6f833a241e65ba4ebc16b` = Flow main head at slice start;
  `git diff --stat 90113e0..HEAD` empty → no commits after PR #19, no implementation occurred.
- HLDspec PR #139: MERGED (2026-07-06T10:48:28Z), head `df944dd4eda5b50e3093ed2ef2de528e28d324a8`,
  merge commit `02862d15e3fea267e42bf3317d6ddc4fa8fbde01` = HLDspec main head; matches the
  expected merge commit byte-for-byte; sole file =
  `docs/flow_journey3/flow-first-controlled-speckit-analyze-record.md` (the analyze record).
- Flow main contains all feature-025 artifacts (spec.md, plan.md, tasks.md, research.md,
  data-model.md, quickstart.md, contracts/). No analyze artifact exists under
  `specs/025-store-transaction-foundation/` — consistent with the stdout-only analyze contract.
- `/speckit.implement` has not run. No SpecKit command ran in this slice.
- Both worktrees clean at slice start (Flow: only pre-existing untracked
  `.hldspec-run.json` / `.hldspec-runs/` control state).

## C1 — constitution/session phasing (CRITICAL in analyze record)

**Re-derived:** analyze record line 133 — constitution `CONTRACT-SESSION-ENFORCEMENT`
(`.specify/memory/constitution.md:50–52`, HLD-009: "Every CLI call carries a recognized
session… reads included") conflicts with the current CLI (accepts `--session` only on
`next`/`done`/`escalate`/`split`), as truthfully disclosed by feature 025's
`quickstart.md:5–8`. Pre-existing runtime-vs-constitution conflict, not introduced by
feature 025 (which traces only HLD-003/HLD-013 and changes no runtime). Grep of
spec.md/plan.md/tasks.md confirms no artifact claims mandatory sessions are implemented.
The analyze record itself offers "explicitly record phased applicability" as a valid
resolution path (lines 173–176, 241–244).

**Owner decision (recorded):** Mandatory session enforcement on every CLI call is
**deferred from feature 025 implementation**.

- Feature 025 may proceed toward store/transaction implementation without changing
  every CLI verb to require `--session`.
- The mandatory-session requirement remains a constitution/HLD-009 target-state
  follow-up (its own future feature; the constitution principle is not diluted).
- Feature 025 must not claim mandatory sessions are implemented (current artifacts
  already comply — quickstart discloses the gap).
- Feature 025 must not implement broad CLI/session enforcement unless separately authorized.
- **C1 no longer blocks feature 025 `/speckit.implement`** once this record is merged.
- The HLD-009/session-enforcement follow-up remains open.

## C2 — constitution header/status (MEDIUM in analyze record)

**Re-derived:** analyze record line 134 — the applied constitution still self-described
as "PROPOSAL ONLY … applied only at CONSTITUTION_APPROVAL_GATE". Authority check:
`.specify/memory/constitution.md` is the **only git-tracked** constitution candidate in
Flow (`git ls-files | grep -i constitution`); other candidates (`constitution.proposed.md`
under `.hldspec-runs/`) are untracked source-package artifacts. Ratification evidence:
commit `696f58d` "constitution: apply approved v2 constitution (CONSTITUTION_APPROVAL_GATE)"
(merged via Flow PR #15, `b8d7c8d`), gate record at HLDspec
`docs/flow_journey2_planning/flow-constitution-approval-gate-record.md` (verified to exist).
Single authoritative file + clear ratification + label-only defect → minimal fix is safe.

**Owner decision (recorded and applied):** minimal header/status label fix only —
title "(PROPOSAL)" suffix removed; Status line changed from "PROPOSAL ONLY … applied
only at CONSTITUTION_APPROVAL_GATE" to "APPLIED. Authored by Journey 2 as a proposal;
approved and applied at `CONSTITUTION_APPROVAL_GATE` (commit `696f58d`, Flow PR #15;
gate record: HLDspec `docs/flow_journey2_planning/flow-constitution-approval-gate-record.md`).
SpecKit owns this applied constitution." No constitutional substance changed
(Source line, Identity, and all rules byte-identical).

- **C2 no longer blocks `/speckit.implement`** — the Flow decision PR (#20) is merged.
- Residual (out of this slice's scope): `plan.md:94` cites "PROPOSAL status — honored
  here as the gating input" — a point-in-time statement that was accurate when plan.md
  passed its Constitution Check; `plan.md` is on this slice's forbidden list and was
  not touched. Cosmetic follow-up at owner discretion.

## G1 — FR-006 mechanical check (MEDIUM coverage finding)

**Re-derived:** analyze record lines 135/179/245 — FR-006 (spec.md:73: loop depends on
exactly CLI + markdown/text, MUST NOT name a specific AI implementation) had no dedicated
verification task; the record's remediation is "extend T011's checklist with an explicit
FR-006 mechanical check (scan core.md/flow.py for AI-implementation references)".

**Owner decision (recorded and applied):** in-place extension of the existing T011 line
(`tasks.md:119`) — an explicit FR-006 mechanical check clause was inserted: scan
`core.md` and `flow.py` for named AI-implementation/model/vendor references (expect zero
matches), confirming the loop depends only on the CLI and markdown/text interfaces.
No new task ID, no renumbering, task count note ("12 total") remains accurate, no
implementation, no test changes now (T011's pre-existing "add any missing test" wording
is unchanged planning text). Scan-only — respects tasks.md's "no task modifies flow.py"
note. Traceability target: FR-006.

- **G1 is resolved as a planning-text extension; non-blocking for `/speckit.implement`.**

## Analyze phase-evidence decision (stdout-only analyze)

**Re-derived:** analyze was stdout-only by contract — zero tracked Flow mutation, no
Flow PR (analyze record lines 111–117, 200–202); no analyze evidence file exists under
`specs/025-store-transaction-foundation/`. The journey3 driver derives the post-analyze
phase from evidence files only (`hldspec/next_feature_readiness.py:177–182`,
`ANALYZE_EVIDENCE_NAMES` = `analyze_report.md`/`analysis.md`), so it cannot observe that
analyze completed.

**Owner decision (recorded):** for feature 025, the merged HLDspec analyze record
(PR #139, merge commit `02862d15e3fea267e42bf3317d6ddc4fa8fbde01`) is **accepted as the
evidence that `/speckit.analyze` completed** (EXECUTED PASSED), despite stdout-only
Flow output.

- The journey3 driver was **not** patched in this slice (explicitly out of scope).
- Follow-up remains open: decide how an analyze gate is evidenced for future features
  (e.g. tracked analyze output, injected phase via HLDspec record reference, or a manual
  phase gate before implement) — the driver currently cannot observe stdout-only analyze
  completion from Flow artifacts.
- The Flow decision PR (#20) is merged; `/speckit.implement` may be considered only
  after this record is also merged and current gates pass — under a separate explicit
  authorization (not yet given).

## Boundaries preserved

- No SpecKit command ran (implement included).
- No implementation, no command wiring, no product/runtime mutation.
- No source-package mutation; no driver mutation.
- `flow.py`, `test_flow.py`, `README.md`, `HLD.md`, feature spec.md/plan.md/research.md/
  data-model.md/quickstart.md/contracts unchanged (pre/post sha256 sentinels verified;
  only `tasks.md` and `.specify/memory/constitution.md` changed, both authorized).
- Ignored/untracked `CLAUDE.md` untouched; `.gitignore` untouched.
- No PR merged by this slice.

## Changes / PRs

- Flow decision PR #20 (https://github.com/saffih/baton-flow/pull/20, branch
  `docs/feature-025-pre-implement-decisions`): **MERGED** 2026-07-06T13:36:52Z with
  expected-head protection; final head `2248a179b1746dcce7a15151a54cae3589f70f96`,
  merge commit `4f616c698f790f69943719d63fb8d973ba533ef9` = Flow main head after merge.
  Exactly 2 files — `.specify/memory/constitution.md` (C2 header/status label only) and
  `specs/025-store-transaction-foundation/tasks.md` (G1 T011 extension only).
- HLDspec branch `docs/record-c1-c2-g1-owner-decisions`: this record only.
- Tests: Flow `python3 -m pytest` green; HLDspec `tests_v2` green (see PR receipts).
- Hidden/bidi scan on all changed files: clean.

## Next action

1. Flow decision PR #20: merged (done). Owner reviews and merges this HLDspec record PR.
2. After this record PR merges: C1 (phased), C2 (header fixed), G1 (T011 extended) no longer block
   feature 025; the analyze phase is evidenced by the merged PR #139 record.
3. Only then prepare a **separate** `/speckit.implement` authorization.
4. Open follow-ups: HLD-009 session-enforcement feature; analyze phase-evidencing
   mechanism for the journey3 driver; optional `plan.md:94` cosmetic label;
   carried-over hygiene items from the analyze record (untracked `.hldspec-run*` in
   Flow; analyze prereq branch-gate bypass asymmetry).

No implementation, command wiring, or merge without separate owner authorization.
