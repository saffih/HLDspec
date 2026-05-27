# HLDspec Development Handoff

## Purpose

This is the canonical handoff protocol for developing the HLDspec repo itself across models, agents, and sessions.

It is different from target-product SpecKit handoff.

## Canonical references

- Handoff protocol: `docs/HLDSPEC_DEVELOPMENT_HANDOFF.md`
- Durable backlog: `docs/HLDSPEC_DEVELOPMENT_BACKLOG.md`
- Runtime handoff packet: `.hldspec-dev/handoff/HANDOFF.md`
- Runtime handoff data: `.hldspec-dev/handoff/HANDOFF.json`

## Core rule

A new model must not depend on hidden chat history.

Every HLDspec development handoff must provide:

- current repo state
- current task/focus
- files changed or intended to change
- relevant architecture context
- invariants
- tests already run
- tests still required
- RunSkeptic status
- open ACTION items
- open CONFLICT items
- next safe step

## Statelessness rule

HLDspec core remains stateless.

Development handoff packets are runtime artifacts, not product state.

Default generated location:

```text
.hldspec-dev/handoff/
  HANDOFF.md
  HANDOFF.json
```

`.hldspec-dev/` is gitignored.

Durable project knowledge belongs in tracked docs, especially:

```text
docs/HLDSPEC_DEVELOPMENT_BACKLOG.md
TASKS.md
AGENTS.md
docs/DOCS_INDEX.md
```

## Required first read

Every model starting HLDspec repo work must read:

```text
AGENTS.md
TASKS.md
docs/HLDSPEC_DEVELOPMENT_HANDOFF.md
docs/HLDSPEC_DEVELOPMENT_BACKLOG.md
docs/DOCS_INDEX.md
docs/CANONICAL_FLOW.md
docs/ARCHITECTURE_V2.md
docs/HLDSPEC_STABILITY_ARCHITECTURE.md
```

Read additional docs only when relevant.

## Model roles

| Tier | Use for | Must not do |
|---|---|---|
| MODEL_ROUTINE | inventory, deterministic extraction, summaries | architecture or promotion decisions |
| MODEL_DEFAULT | focused edits, tests, small docs/code changes | approve architecture or source-of-truth changes |
| MODEL_STRONG | bounded refactors, adapter seams, validators, tests | unresolved architecture conflicts |
| MODEL_CRITICAL | architecture, contracts, source-of-truth, gates, RunSkeptic verdicts | broad edits without decomposition |
| HUMAN | product intent, approvals, tradeoffs, risky transitions | hidden approval |

Rule:

```text
Weakest sufficient model creates.
Strongest necessary model promotes.
```

## Required invariants

1. Source HLD is read-only. Workspace copy only.
2. SpecKit is not invoked until approval gates pass.
3. Final SpecKit specs are not written manually by HLDspec.
4. Application code is not implemented by HLDspec.
5. Gate machines gate; scripts generate.
6. Dependency graph and invocation queue must not diverge.
7. RunSkeptic must use the real current `skeptic.md`.
8. Patch scripts must be syntax checked before handoff.
9. Dirty-tree work must be handled explicitly.
10. HLDspec runtime state belongs outside core code.
11. Durable backlog belongs in `docs/HLDSPEC_DEVELOPMENT_BACKLOG.md`.
12. Ad hoc agent-created docs follow `docs/AGENT_ARTIFACT_HYGIENE.md`.

## Generate a handoff packet

```bash
python3 scripts/hldspec_dev_handoff.py \
  --focus "describe the current change" \
  --from-agent codex \
  --to-agent claude \
  --model-tier MODEL_STRONG
```

## Acceptance criteria

Another model can continue safely without reading the full chat history and without guessing:

- what changed
- what is intended
- what must not be touched
- which docs are authoritative
- which tests prove the work
- what the next safe step is

## Gap handoff standard

When HLDspec repo work is handed between agents, models, or sessions, create or update a Gap Handoff using `docs/HLDSPEC_GAP_HANDOFF_TEMPLATE.md`.

A Gap Handoff records current status, dirty files, known gaps, next safe patch, tests actually run, and forbidden actions. It is not architecture truth and must point back to `README.md`, `docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md`, `docs/SPECKIT_PROXY_PROTOCOL.md`, and `docs/SPECKIT_SLICE_CONTROL.md`.

## Gap handoff rule

When handing HLDspec repo work between agents or sessions, produce a gap handoff
using `docs/HLDSPEC_GAP_HANDOFF_TEMPLATE.md`. The gap handoff is current status,
not architecture truth.

The gap handoff must use the artifact contract style from
`docs/HLDSPEC_ARTIFACT_CONTRACT_STYLE.md`: Inputs, Authority, Allowed Actions,
Forbidden Actions, Expected Outputs, Validation Required, Stop Conditions, Report
Format, Next Owner, and Evidence.
