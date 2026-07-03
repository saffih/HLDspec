# Flow SDD-Ready Gate — Owner Acceptance of Provisional Risks

Date: 2026-07-04

Status: **RATIFIED** — owner acceptance recorded.

## Decision

Human approver: Hadas / project owner.

The project owner accepts the six provisional-spec risks recorded in
`flow-sdd-ready-gate-v2.md` (PR #124, merged as `17ebf9b`). This promotes the
Flow SDD-ready gate verdict from **ACTION** to **PASS** for the next approved
planning gate only.

## Accepted risks

| # | Section | Risk | Provisional field | Revisit trigger |
|---|---|---|---|---|
| 1 | HLD-001 (purpose) | MEDIUM | HLD-SPECS: provisional | assign when the first spec citing this section is drafted |
| 2 | HLD-002 (vocabulary) | LOW | HLD-SPECS: provisional | assign when the first spec citing this section is drafted |
| 3 | HLD-006 (escalation triggers) | MEDIUM | HLD-SPECS: provisional | assign when the first spec citing this section is drafted |
| 4 | HLD-011 (scope boundary) | LOW | HLD-SPECS: provisional | assign when the first spec citing this section is drafted |
| 5 | HLD-012 (technology) | LOW | HLD-SPECS: provisional | assign when the first spec citing this section is drafted |
| 6 | HLD-017 (requirements/candidates) | LOW | HLD-SPECS: provisional | assign when the first spec citing this section is drafted |

All six revisit triggers are preserved. Specs are assigned when they exist,
not before.

## What PASS means

- Journey 2 may decompose features using the 11 constitution-backed sections.
- Journey 2 flags or defers decomposition for the 6 provisional sections
  until specs exist.
- The revisit trigger ensures specs are assigned when the first spec citing
  each section is drafted — not manufactured in advance.

## What PASS does not authorize

- Starting Journey 2 or Journey 3.
- Invoking SpecKit.
- Wiring commands.
- Creating backlog or implementation scope.
- Mutating `/Users/saffi/code/flow`.
- Closing J0-12 globally.
- Treating candidate capabilities (HLD-017) as implemented commitments.

Journey 2 requires its own explicit start authorization.

## Formal counts (unchanged)

```
unresolved = 0
provisional = 6 (accepted)
```

Gate verdict promotion: ACTION → PASS (for next approved planning gate).

## Provenance

- Gate assessment: `flow-sdd-ready-gate-v2.md` (PR #124, commit `7c5a9dc`,
  merge commit `17ebf9b`)
- Drift disposition: `flow-drift-disposition.md` (PR #123)
- Owner decisions: `flow-hld-hardening-owner-decisions.md` (PR #120)
- Flow HLD v2 hash: `3c376ae9917b05d09d71fd73037b41a800eecbe51eaa5167481f1db11cf7e5d0`
