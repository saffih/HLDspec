# HLDspec RunSkeptic Gap Review - Current State to Goal

Date: 2026-05-23

## Goal

HLDspec should be usable as a judge-led product that takes an HLD, finds the safe next checkpoint, explains the plan, prevents context-only feature selection, and prepares bounded SpecKit handoff only after approval.

## Current state after this patch

HANDLED:

- Product scenarios are documented.
- Formal user stories and acceptance tests are documented.
- Section classifier separates context-only and governance sections from buildable candidates.
- Planner has regression coverage proving context-only sections do not become planned specs.
- Use-case/API map is executable and produces JSON and markdown.
- First read-only flow builds the map before plan/prework package.
- Prework package presents a use-case/API case.
- Quality gate can detect context-only first-feature handoff when a map exists.

## Remaining gaps

### Gap 1 - State and status are still not the product front door

Issue:

- `hldspec_state.json` exists in the flow, but the user still needs to know which scripts/artifacts to inspect.

Needed:

- `scripts/hldspec_status.sh`
- stable output contract:
  - current stage
  - current checkpoint
  - controlling artifact
  - human decision needed
  - next allowed action

Decision: DECOMPOSE into a status-wrapper patch.

### Gap 2 - Interview/checkpoint answering is not implemented as a simple API

Issue:

- Decision queues exist, but the user does not yet have a simple way to answer them and rerun correctly.

Needed:

- `scripts/hldspec_interview.sh`
- answer recording into controlling JSON
- rerun option
- no repeated questions already answered

Decision: DECOMPOSE after status wrapper.

### Gap 3 - Source-HLD-affecting feedback queue is missing

Issue:

- Docs say architecture-changing feedback must not be lost, but there is no dedicated source update queue yet.

Needed:

- feedback classifier
- source update queue JSON/MD
- rebuild affected artifacts policy
- explicit source-HLD modification approval

Decision: DECOMPOSE after interview wrapper.

### Gap 4 - SpecKit proxy is still unsafe to automate

Issue:

- Proxy dossier exists, but complete phase execution with question answering and escalation is not ready.

Needed:

- approved feature queue
- one-feature one-phase runner
- evidence-bound answer policy
- escalation records
- changed-file record
- no implementation without explicit approval

Decision: CONFLICT until state/interview/approval ownership is stable.

### Gap 5 - Use-case/API extraction is heuristic

Issue:

- The map is useful as a prework gate, but it is not semantic proof of system behavior.

Needed:

- more fixtures from real HLDs
- stronger extraction rules for actors, journeys, interfaces, data objects
- red/green tests for known bad first-feature cases

Decision: FIX incrementally with fixtures.

## Focused RunSkeptic decision

HANDLED in this patch:

- user stories
- holistic RunSkeptic review
- executable use-case/API map
- current-state-to-goal gap review

CONFLICTS / not ready:

- full SpecKit proxy automation
- changing unknown default from SPEC_CANDIDATE to REVIEW_NEEDED
- source-HLD feedback mutation without explicit approval

## Next recommended patch

Patch 4 should be:

```text
hldspec_status wrapper + state contract hardening
```

Acceptance tests:

- Given a workspace blocked on conversion, status prints CONVERSION_CHECKPOINT and points to the conversion queue.
- Given a workspace approval-ready for prework, status prints SPECKIT_PREWORK_APPROVAL_GATE and points to the prework package.
- Given missing workspace artifacts, status reports NO_WORKSPACE or RAW_HLD_INSPECTED instead of failing silently.
