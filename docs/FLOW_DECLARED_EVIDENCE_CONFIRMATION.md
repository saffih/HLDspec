# Flow Declared Evidence Human Confirmation

**Status:** human confirmation pass for the 10 declared evidence items from
RT-2 (DECLARED-001…010), per the checklist in
`docs/FLOW_JOURNEY1_PLANNING_SCOPE.md`. Records explicit owner decisions of
2026-07-03. It authorizes nothing beyond recording those decisions.

- This does not start Journey 1 execution.
- This does not authorize HLD writing.
- This does not authorize SpecKit.
- This does not authorize command wiring.
- This does not mutate `/Users/saffi/code/flow`.
- This does not create backlog or implementation scope.
- J0-17 remains **BLOCKED** after this doc.
- J0-12 provenance remains open unless separately resolved.
- Any AMEND / REJECT / UNRESOLVED item blocks authoritative HLD writing until
  re-reviewed through Journey 0 declared-evidence review.

## Purpose

Complete the human confirmation checklist defined in
`docs/FLOW_JOURNEY1_PLANNING_SCOPE.md`: an explicit
confirm / amend / reject / unresolved decision per declared item, with
DECLARED-005 and DECLARED-009 resolved explicitly. This is the authority
checkpoint the planning scope required before any future authoritative HLD
writing.

## Source inputs

- `docs/FLOW_JOURNEY1_PLANNING_SCOPE.md` (PR #114 — checklist and questions)
- `docs/FLOW_JOURNEY1_PLANNING_JUSTIFICATION.md` (PR #113)
- `docs/journey0_real_target_dry_runs/flow-journey0-declared-evidence-dry-run.md`
  (RT-2 — the declared items and provenance)
- `docs/HLDSPEC_DEVELOPMENT_BACKLOG.md` (J0-12, J0-16, J0-17 status)
- Owner decisions given interactively on 2026-07-03 (recorded below)

No target-repo files were read. No new evidence was collected. No target file
contents or snippets appear here.

## Provenance caveat

Carried forward verbatim:

> Declared evidence is user-approved but **not automatically validated as
> product truth**. It was drafted by reading the three allowed target files and
> approved by a human for dry-run use, not ratified as authoritative product
> definition. Additionally, the full Journey 0 provenance model is still open
> (backlog J0-12: PROVENANCE_OPEN). Any Journey 1 planning output must carry
> this caveat forward verbatim, and HLD writing must not begin until the
> declared items are human-confirmed as product truth.

This confirmation pass resolves the "human-confirmed" clause for the CONFIRM
items only. It does not resolve J0-12, does not lift J0-17, and RT-2 PASS
still means evidence sufficiency for Journey 1 consideration — not Journey 1
authorization.

## Confirmation table

| Item | Decision | Usable for future Journey 1 planning | May anchor authoritative HLD writing |
|---|---|---|---|
| DECLARED-001 durable-baton task management | CONFIRM | yes | no — see impact section |
| DECLARED-002 fork-join workflow (escalation, splitting, dependency gates) | CONFIRM | yes | no — see impact section |
| DECLARED-003 AI session runners via CLI | CONFIRM | yes | no — see impact section |
| DECLARED-004 human operator as actor | CONFIRM | yes | no — see impact section |
| DECLARED-005 CLI in; SQLite state + markdown projections out | AMEND | conditional — amended wording only | no — J0 re-review required |
| DECLARED-006 human replies drive state transitions | CONFIRM | yes | no — see impact section |
| DECLARED-007 core task loop | CONFIRM | yes | no — see impact section |
| DECLARED-008 escalation/resume workflow | CONFIRM | yes | no — see impact section |
| DECLARED-009 one open escalation per task | AMEND | conditional — amended wording only | no — J0 re-review required |
| DECLARED-010 no web UI / HTTP / sockets / daemons / pools | REJECT | no — must be removed/replaced | no — must be removed/replaced |

Decision notes:

- **DECLARED-001 — CONFIRM.** Owner: durable-baton task management across AI
  handoffs stands as flow's core capability.
- **DECLARED-002 — CONFIRM.** Owner: "we need all — task, fork-join, etc."
  Escalation, splitting, and dependency gates are all current intended
  capabilities; none dropped or superseded.
- **DECLARED-003 — CONFIRM.** Owner: yes; AI session runners (Claude, Devin,
  Codex) via CLI are the intended primary machine actors and the named set is
  current.
- **DECLARED-004 — CONFIRM.** Owner: the human operator role (creates tasks,
  steers, holds authority decisions) is complete and correctly bounded.
- **DECLARED-005 — AMEND.** See special resolution below.
- **DECLARED-006 — CONFIRM.** Owner: human replies in; task state transitions
  + baton updates out stands as the interaction contract.
- **DECLARED-007 — CONFIRM.** Owner: the loop create → claim → read baton →
  work → note → done/escalate/split → loop stands as the current lifecycle.
- **DECLARED-008 — CONFIRM.** Owner: escalate → human replies → task wakes →
  re-claim → continue stands as the escalation flow.
- **DECLARED-009 — AMEND.** See special resolution below.
- **DECLARED-010 — REJECT.** Owner: "we want all — but it was sliced out. We
  can have that back; HLDspec knows how to handle lots of features." The
  exclusion list (no web UI, HTTP API, Unix sockets, daemons, pools) is
  slicing residue, not intentional product limits. All excluded capabilities
  are back in scope as candidate future features. The item may not be used as
  a product-limit claim and must be removed or replaced through Journey 0
  declared-evidence review before any HLD writing.

## DECLARED-005 special resolution

- **SQLite is: IMPLEMENTATION_DETAIL.** Replaceable without product change.
  It must not be written into HLD content as a promised storage contract.
- **Markdown projections are: PRODUCT_SURFACE.** Owner clarified their roles;
  wording drafted by this session from that clarification (owner: "I
  clarified, you make the wording").

Amended wording for DECLARED-005:

> CLI commands in; task state out. Persistent state storage is an
> implementation detail (currently SQLite, replaceable without product
> change). Markdown projections are product surface with three promised
> roles: (1) integration surface for agents, (2) context state for work in
> progress, (3) user-facing context and reporting in reports.

## DECLARED-009 special resolution

- **One-open-escalation invariant is: STALE_DESIGN_RESIDUE.** Owner decision
  2026-07-03: a task **may have multiple escalations open concurrently**. The
  one-open-escalation-per-task structural invariant from HLD-005 must not be
  encoded as a product constraint.
- This supersedes the 2026-06-28 brownfield-review owner decision of "serial
  escalation".

Amended wording for DECLARED-009:

> A task may have multiple escalations open concurrently. No
> one-open-escalation-per-task invariant applies.

## Items confirmed

DECLARED-001, DECLARED-002, DECLARED-003, DECLARED-004, DECLARED-006,
DECLARED-007, DECLARED-008 (7 items).

## Items amended

DECLARED-005, DECLARED-009 (2 items — amended wording recorded above). Each
must pass Journey 0 declared-evidence re-review before HLD writing.

## Items rejected

DECLARED-010 (1 item — rejection reason recorded above). It must be removed
or replaced before any HLD writing.

## Items unresolved

None.

## Impact on future Journey 1 planning

- The 7 CONFIRM items may be used for future Journey 1 planning, cited by
  DECLARED id and RT-2 provenance.
- DECLARED-005 and DECLARED-009 may be used for planning **only** with their
  amended wording above.
- DECLARED-010 may not be used. Planning must not treat the old exclusion
  list as a product boundary; the replacement limits item (if any) comes from
  Journey 0 re-review.
- This confirmation pass is a planning input. It does not start Journey 1
  execution, and the future Journey 1 execution prompt remains blocked by the
  exit criteria in `docs/FLOW_JOURNEY1_PLANNING_SCOPE.md`.

## Impact on authoritative HLD writing

No item may anchor authoritative HLD writing yet:

- Exit criterion 4 of the planning scope is unmet: the amended items
  (DECLARED-005, DECLARED-009) and the rejected item (DECLARED-010) must be
  re-reviewed through Journey 0 declared-evidence review and the resulting
  evidence set re-approved.
- Exit criterion 5 is unmet: J0-17 remains BLOCKED and J0-12 provenance
  remains open.
- There is no partial unlock: the 7 confirmed items do not authorize HLD
  writing while amended/rejected items are outstanding.

## Stop conditions

Unchanged from `docs/FLOW_JOURNEY1_PLANNING_SCOPE.md`. In addition, any use
of DECLARED-005 or DECLARED-009 with pre-amendment wording, or any use of
DECLARED-010 as a product limit, is a stop condition returning to human
review.

## Next action

Prepare a Journey 0 declared-evidence re-review / correction slice covering
the two amended items (DECLARED-005, DECLARED-009) and the rejected item
(DECLARED-010), producing a corrected, re-approved evidence set. Do not
auto-start Journey 1 execution; J0-17 remains BLOCKED until human and project
approval after blocker and stabilization review (including J0-12).
