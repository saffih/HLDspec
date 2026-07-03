# Flow Corrected Declared-Evidence Dry Run Report

## Purpose

Re-run Journey 0 against the same bounded `flow` target/path set using the
corrected declared-evidence set after PR #115.

This report records the Journey 0 dry-run result only. It does not start Journey
1 execution, authorize HLD writing, authorize SpecKit, wire commands, mutate
`/Users/saffi/code/flow`, create backlog, or create implementation scope.

## Source inputs

- **Target repo:** `/Users/saffi/code/flow`
- **Allowed relative paths:** `README.md`, `HLD.md`, `core.md`
- **Run intent:** Re-run Journey 0 dry-run against the same exact flow
  target/path set using the corrected declared evidence set after PR #115. This
  tests whether the amended/replaced evidence correction produces PASS or
  ACTION. This does not authorize Journey 1.
- **Source reports/docs:**
  - `docs/FLOW_DECLARED_EVIDENCE_CONFIRMATION.md`
  - `docs/journey0_real_target_dry_runs/flow-journey0-declared-evidence-dry-run.md`

## PR #115 confirmation basis

PR #115 confirmed seven declared evidence items unchanged:

- `DECLARED-001`
- `DECLARED-002`
- `DECLARED-003`
- `DECLARED-004`
- `DECLARED-006`
- `DECLARED-007`
- `DECLARED-008`

PR #115 required re-review for:

- `DECLARED-005`, amended.
- `DECLARED-009`, amended.
- `DECLARED-010`, rejected and requiring replacement.

## Corrected declared evidence set

The corrected set contains 10 declared evidence items:

| Item | Source type | Status in this run |
| --- | --- | --- |
| `DECLARED-001` | `product_capability` | Unchanged from PR #115 CONFIRM |
| `DECLARED-002` | `product_capability` | Unchanged from PR #115 CONFIRM |
| `DECLARED-003` | `product_actor` | Unchanged from PR #115 CONFIRM |
| `DECLARED-004` | `product_actor` | Unchanged from PR #115 CONFIRM |
| `DECLARED-005` | `product_input_output` | Amended: SQLite is implementation detail; markdown projections are product surface |
| `DECLARED-006` | `product_input_output` | Unchanged from PR #115 CONFIRM |
| `DECLARED-007` | `product_workflow` | Unchanged from PR #115 CONFIRM |
| `DECLARED-008` | `product_workflow` | Unchanged from PR #115 CONFIRM |
| `DECLARED-009` | `product_workflow` | Amended: multiple concurrent escalations may be open if references, ownership, routing, state, and context integrity remain clear |
| `DECLARED-010` | `product_limit` | Replacement product limit from corrected human-approved scope |

Source-type coverage:

| Source type | Count |
| --- | ---: |
| `product_capability` | 2 |
| `product_actor` | 2 |
| `product_input_output` | 2 |
| `product_workflow` | 3 |
| `product_limit` | 1 |

No product-surface source type is missing.

## Retired / rejected evidence

The rejected old `DECLARED-010` exclusion-list claim is not used as
product-limit evidence in this run.

Old rejected claim, retired: no web UI, HTTP API, Unix sockets, daemons, or
worker pools.

## Replacement product_limit status

Replacement `DECLARED-010` is used as the only `product_limit` item.

Its corrected meaning is that interfaces and infrastructure may expand when
they support the core baton/context management goal, but no interface or
infrastructure may bypass or weaken baton/context integrity, durable task state,
stable IDs, explicit references, escalation traceability, session/log links,
copy-pasteable context, or human authority over decisions.

Replacement `DECLARED-010` is human-declared corrected evidence, not
automatically validated product truth.

## Target/path bounds

- **Target root exists:** yes
- **Target root is directory:** yes
- **Target root is `/`:** no
- **Target root is HLDspec repo:** no
- **Allowed paths are relative:** yes
- **Allowed paths are contained by target root:** yes
- **Allowed paths exist:** yes
- **Allowed paths match RT-1/RT-2:** yes

Target git status had pre-existing untracked `.hldspec-run.json` and
`.hldspec-runs/`. This report's no-mutation proof is therefore scoped to the
exact allowed paths listed above.

## Evidence collected

Journey 0 produced 13 evidence items:

| Source type | Count |
| --- | ---: |
| `doc_file` | 2 |
| `hld_fragment` | 1 |
| `product_capability` | 2 |
| `product_actor` | 2 |
| `product_input_output` | 2 |
| `product_workflow` | 3 |
| `product_limit` | 1 |

Generic structural evidence was collected from the allowed paths, but generic
file/doc/code evidence remains observational only and is not PASS-capable by
itself.

## Product surface result

| Product surface field | Count |
| --- | ---: |
| Product capabilities | 2 |
| Users and actors | 2 |
| Inputs and outputs | 2 |
| Workflows | 3 |
| Known limits | 1 |
| Unknowns | 0 |

## Gaps

No Journey 0 gap items were produced.

## Product decisions

No open, deferred, or decided product decisions were produced.

## Draftability verdict

- **Verdict:** PASS
- **Blocking items:** none
- **Required human decisions:** none
- **Accepted evidence refs:** 13

PASS means this corrected evidence set is sufficient for Journey 1
consideration only. It does not authorize Journey 1 execution, HLD writing,
SpecKit, command wiring, target mutation, backlog, or implementation scope.

## HLD update-plan result

Journey 0 produced an HLD update-plan artifact with these section names:

- Product capabilities
- Users and actors
- Inputs and outputs
- Workflows
- Known limits

The plan artifact is not HLD prose and does not write or authorize HLD content.
It contains no backlog.

## No-mutation proof

Before/after hashes matched for the exact allowed paths:

| Path | Before | After | Match |
| --- | --- | --- | --- |
| `README.md` | `4dc69a9b...313df` | `4dc69a9b...313df` | yes |
| `HLD.md` | `77a10696...ec962` | `77a10696...ec962` | yes |
| `core.md` | `f684e7be...2b039` | `f684e7be...2b039` | yes |

The Journey 0 dry-run library also reported `target_unchanged = True`.

## Provenance caveat

J0-12 remains open. The corrected declared evidence is human-declared evidence
for Journey 0 review. It is not automatically validated product truth and must
not be silently converted into authoritative HLD content.

## Boundaries preserved

- This does not start Journey 1 execution.
- This does not authorize HLD writing.
- This does not authorize SpecKit.
- This does not authorize command wiring.
- This does not mutate `/Users/saffi/code/flow`.
- This does not create backlog or implementation scope.
- This does not lift J0-17.
- This does not close J0-12.
- Rejected old `DECLARED-010` is not used as product-limit evidence.
- Replacement `DECLARED-010` is human-declared corrected evidence, not
  automatically validated product truth.

## Verdict comparison: RT-2 vs corrected run

| Run | Declared evidence | Verdict | Product surface coverage | Notes |
| --- | --- | --- | --- | --- |
| RT-2 | 10 items, including old `DECLARED-010` | PASS | 5/5 categories | Later review amended `DECLARED-005`, amended `DECLARED-009`, and rejected old `DECLARED-010` |
| Corrected run | 10 items, with amended `DECLARED-005`, amended `DECLARED-009`, and replacement `DECLARED-010` | PASS | 5/5 categories | Old `DECLARED-010` retired; replacement product limit used |

## Next action

Prepare a J0-12/J0-17 unblock review. Do not auto-start Journey 1 execution.
