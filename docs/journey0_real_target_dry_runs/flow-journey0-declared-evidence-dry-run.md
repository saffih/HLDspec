# Journey 0 Declared-Evidence Dry Run Report: flow (RT-2)

## Run context

- **Date:** 2026-07-03
- **HLDspec branch:** proof/journey0-flow-declared-evidence-dry-run
- **HLDspec base:** main @ f109b8b (PR #111 merged)
- **Run intent:** Re-run Journey 0 dry-run against the same exact flow target/path set as RT-1, this time with explicit declared product-surface evidence, to test declared-evidence composition and verdict progression. This does not authorize Journey 1.

## RT-1 baseline

- **RT-1 report:** docs/journey0_real_target_dry_runs/flow-journey0-dry-run.md
- **RT-1 verdict:** ACTION (empty declared evidence)
- **RT-1 evidence:** 3 items (doc_file: 2, hld_fragment: 1)
- **RT-1 product surface:** all zeros, 1 unknown
- **RT-1 no-mutation:** clean
- **RT-1 next action:** "Provide explicit declared product-surface evidence and re-run"

## Target/path bounds

- **Target repo:** /Users/saffi/code/flow
- **Allowed relative paths:** README.md, HLD.md, core.md (identical to RT-1)
- **Path escape check:** PASS
- **Paths exist:** all 3 confirmed
- **Target hashes unchanged since RT-1:** confirmed (all 3 SHA-256 match)

## Declared product-surface evidence

10 items, user-approved, 2 per category. Source: human-declared from allowed target files. Not automatically validated as product truth.

| # | Source type | Summary (truncated) | Provenance |
|---|---|---|---|
| 1 | product_capability | Task management with durable baton across AI handoffs | README.md, HLD-001 |
| 2 | product_capability | Fork-join workflow: escalation + splitting + dependency gates | HLD-004, HLD-005 |
| 3 | product_actor | AI session runners (Claude, Devin, Codex) via CLI | HLD-003, core.md |
| 4 | product_actor | Human operator: creates tasks, steers, authority decisions | README.md, HLD-006 |
| 5 | product_input_output | CLI commands in; SQLite state + markdown projections out | README.md, HLD-003 |
| 6 | product_input_output | Human replies in; task state transitions + baton updates out | core.md, HLD-005 |
| 7 | product_workflow | Create → claim → read baton → work → note → done/escalate/split → loop | core.md |
| 8 | product_workflow | Escalate → human replies → task wakes → re-claim → continue | core.md, HLD-005 |
| 9 | product_limit | One open escalation per task (structural invariant) | HLD-005 |
| 10 | product_limit | No web UI, HTTP API, Unix sockets, daemons, pools (HLD-011) | README.md |

## Evidence collected

| Source type | Count | Source |
|---|---|---|
| doc_file | 2 | structural (README.md, core.md) |
| hld_fragment | 1 | structural (HLD.md) |
| product_capability | 2 | declared |
| product_actor | 2 | declared |
| product_input_output | 2 | declared |
| product_workflow | 2 | declared |
| product_limit | 2 | declared |
| **Total** | **13** | 3 structural + 10 declared |

## Product surface result

| Field | RT-1 | RT-2 |
|---|---|---|
| observed_capabilities | 0 | 2 |
| observed_users_or_actors | 0 | 2 |
| observed_inputs_outputs | 0 | 2 |
| observed_workflows | 0 | 2 |
| known_limits | 0 | 2 |
| unknowns | 1 | 0 |

All 5 product-surface categories populated from declared evidence. Unknown count dropped to 0.

## Spec inventory result

- **Specs found:** 0
- Unchanged from RT-1. Spec inventory requires deeper analysis beyond Journey 0 scope.

## Gaps

- **Gaps found:** 0
- Unchanged from RT-1.

## Product decisions

- **Decisions recorded:** 0
- No product decisions triggered. All declared evidence was accepted without conflict.

## Draftability verdict

- **Verdict:** PASS
- **Reason:** Accepted observed evidence and explicit product-surface evidence are sufficient for Journey 1.
- **Blocking items:** none
- **Required human decisions:** none
- **Safe next action:** Proceed to Journey 1 HLD authoring/hardening using accepted Journey 0 evidence and explicit product-surface evidence only.
- **Accepted evidence refs:** COLLECTED-001 through COLLECTED-003, DECLARED-001 through DECLARED-010 (all 13)

## HLD update-plan result

| Section | Evidence refs |
|---|---|
| Product capabilities | DECLARED-001, DECLARED-002 |
| Users and actors | DECLARED-003, DECLARED-004 |
| Inputs and outputs | DECLARED-005, DECLARED-006 |
| Workflows | DECLARED-007, DECLARED-008 |
| Known limits | DECLARED-009, DECLARED-010 |

- **Decisions required before writing:** none
- **Known stale material:** none
- **Open questions:** none
- **Contains backlog:** no
- **Contains helper handoff:** no

## No-mutation proof

| File | Before SHA-256 | After SHA-256 | Match |
|---|---|---|---|
| README.md | 4dc69a9b…313df | 4dc69a9b…313df | YES |
| HLD.md | 77a10696…ec962 | 77a10696…ec962 | YES |
| core.md | f684e7be…2b039 | f684e7be…2b039 | YES |

- **Library assertion:** target_unchanged = True
- **Independent hash check:** all 3 match before/after and match RT-1
- **Target mutation:** NONE

## Provenance caveat

- Declared evidence is user-approved but not automatically validated as product truth.
- Evidence was drafted by reading allowed target files (README.md, HLD.md, core.md) and presented for human approval before use.
- Generic file evidence (doc_file, hld_fragment) contributed to the evidence pack but did not independently drive the PASS verdict — declared evidence did.
- The PASS verdict reflects evidence sufficiency for Journey 1 consideration, not Journey 1 authorization.

## Boundaries preserved

- No Journey 1 started
- No command-surface wiring added
- No SpecKit invoked
- No target mutation
- No HLD content written
- No backlog or implementation scope created
- No real-target readiness claimed beyond this dry-run result
- Declared evidence is prompt/user-declared and not automatically validated as product truth
- Generic file evidence cannot PASS alone — RT-1 confirmed this

## Verdict progression

| Run | Declared evidence | Verdict | Product surface coverage |
|---|---|---|---|
| RT-1 | empty | ACTION | 0/5 categories, 1 unknown |
| RT-2 | 10 items (2 per category) | PASS | 5/5 categories, 0 unknowns |

The verdict progressed from ACTION to PASS solely due to explicit declared product-surface evidence. This confirms:
1. Generic file evidence alone does not produce PASS (RT-1 proved this).
2. Declared evidence correctly composes with structural evidence.
3. The draftability gate responds to explicit product-surface coverage.

## Next action

RT-2 verdict is PASS with no mutation. To advance:

1. Review whether Journey 1 planning PR is justified for flow.
2. Do not auto-start Journey 1 — human decision required.
3. Declared evidence should be reviewed for accuracy before any Journey 1 use.
