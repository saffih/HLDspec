# HLDspec Repository Migration Plan

A **phased** plan for making the repository express the product architecture in
`docs/ARCHITECTURE_LAYERS.md`. This is a migration *plan*, not a migration: the
first phase moves nothing.

## Purpose

Over time the repo accumulated scripts, docs, compatibility files, and patches.
The goal is to make every tracked top-level file or directory have **one clear
classification** so a maintainer can answer quickly: what is the product, what
does the user do, what does the agent do, what is active, what is compatibility,
what is legacy, what is generated, and what tests protect it.

## Migration principle

Do **not** move everything at once. The order is deliberate:

1. Define the intended layer map (`ARCHITECTURE_LAYERS.md`).
2. Classify every tracked top-level file/dir (this doc).
3. Add anti-drift tests that lock the intended shape.
4. Migrate only **low-risk docs/pointers**.
5. Isolate compatibility/V1 surfaces **only after** references are proven safe.
6. Production hardening after layout and UX are aligned.

A move happens only when references and tests prove it safe. **Renaming a public
concept requires updating its tests and docs in the same change.**

## Phases

### Phase 0 — Canonical layer map, **no moves**

Create `ARCHITECTURE_LAYERS.md` and this plan. **No broad file moves** in this
phase — no files are moved, renamed, or deleted. Output: the layer map, the
classification table below, and the contract test
`tests_v2/test_architecture_layers_contract.py`.

- **Tests required before any move:** none yet (no moves). The contract test must
  pass.
- **Rollback / revert rule:** docs-and-tests only; revert the commit to undo.

### Phase 1 — Public UX alignment (agent one-liner first)

Make the agent one-liner the documented front door everywhere; reframe script
commands as the internal/agent tool surface. (Landed on `main`: README,
`USER_RUN_MODEL.md`, and `HLDSPEC_TERMINOLOGY_AND_FLOW.md` now lead with the agent
one-liner.)

- **Tests required before any move:** the agent-first UX contract test and the
  product-readiness docs test must pass; no script path may appear as the primary
  path in the README "Main user workflow" body.
- **Rollback / revert rule:** docs/tests only; revert the commit. No runtime
  impact.

### Phase 2 — Canonical terminology and source-of-truth docs

Ensure `HLDSPEC_TERMINOLOGY_AND_FLOW.md` is the single canonical terminology and
command-surface source and every doc defers to it.

- **Tests required before any move:** terminology/flow docs test and anti-drift
  contracts test must pass.
- **Rollback / revert rule:** docs/tests only; revert the commit.

### Phase 3 — Complete top-level classification  *(enforced)*

The classification table below covers **every** tracked top-level entry, with no
file left as "just there". This is now **enforced**:
`tests_v2/test_repo_top_level_classification.py` reads the tracked top-level
entries from `git ls-files` and fails if any is missing a backticked row in the
table. Adding a new top-level file/dir therefore requires classifying it in the
same change.

- **Tests required before any move:** repo-layout readability test plus the
  top-level classification test (`test_repo_top_level_classification`) must pass.
- **Rollback / revert rule:** docs/tests only; revert the commit.

### Phase 4 — Low-risk doc/pointer migration only

Move or consolidate **docs and pointers** that no code imports (e.g. a clearer
home for `Dev`, `TERMINOLOGY.md`). No source or test moves.

- **Tests required before any move:** grep proves no code/test references the
  path; full `tests_v2` is green before and after each move.
- **Rollback / revert rule:** `git mv` is reversible; revert restores the path.
  Re-run the full suite after revert.

### Phase 5 — Compatibility / V1 isolation, only after references proven

Relocate or clearly fence V1 surfaces (`hld_spec_sync.py`,
`hld_spec_downstream.py`) **only after** proving every caller
(`scripts/first_run_readonly.sh`, `scripts/full_cycle_smoke.sh`, `poc/run_poc.sh`,
`tests/`) is updated. **V1 compatibility files are not deleted in this plan.**

- **Tests required before any move:** `tests/` (V1 integration) and full
  `tests_v2` green; every caller updated and exercised in the same change.
- **Rollback / revert rule:** revert the move commit; re-run `tests/` and
  `tests_v2` to confirm the V1 pipeline is wired again.

### Phase 6 — Production hardening

Only after layout and UX are aligned: install/release story, CI, recovery/rollback
runbook, security sign-off, real-HLD pilots. **Production-ready remains NO** until
these are met.

- **Tests required before any move:** the full readiness gate
  (`scripts/check_product_readiness.sh`) plus CI green.
- **Rollback / revert rule:** packaging/CI changes are additive; revert the
  offending commit without touching product source.

## Current top-level classification

Every tracked top-level file/dir, with one category each. Categories map to the
layers in `ARCHITECTURE_LAYERS.md`.

| Path | Category | Notes |
|---|---|---|
| `README.md` | docs — public product entry | Conceptual front door; Layer 1/2 surface. |
| `AGENTS.md` | docs — agent entry | Agent bootstrap; defers to canonical terminology. |
| `CLAUDE.md` | docs — session bootstrap | Project reference for a new session. |
| `TASKS.md` | docs — backlog | Living P0/P1/P2 task list. |
| `Dev` | scratch/session pointer | Session-restart pointer; no active code references it. May move in Phase 4. |
| `TERMINOLOGY.md` | legacy/reference | Older root glossary; canonical source is `docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md`. May move in Phase 4. |
| `HLD_FORMAT.md` | docs — reference | Grepable HLD input format consumed by the V1 pipeline. |
| `HLD_GENERATION.md` | docs — reference | How to author/convert an HLD into that format. |
| `LICENSE` | repo meta | License. |
| `.gitattributes`, `.gitignore` | repo meta | Git config. |
| `.github/` | repo meta — CI | GitHub Actions workflows; currently runs the `tests_v2` baseline. |
| `pytest.ini` | repo meta — test config | Pytest discovery config for active `tests/` and `tests_v2/`; excludes reference-only `tests_legacy/`. |
| `hld_map.py` | active core — shared parser | Shared HLD parser; imported by V2 (`hldspec/hld_marking.py`) and V1. Not legacy. |
| `hld_spec_sync.py` | compatibility/V1 | V1 pipeline; still wired (`first_run_readonly.sh`, `tests/`). Not active V2 core. |
| `hld_spec_downstream.py` | compatibility/V1 | V1 pipeline; invoked by `poc/run_poc.sh`. Not active V2 core. |
| `hldspec/` | active core source | Layer 3: state machines, contracts, renderers, operator state, readiness. Do not move in this plan. |
| `scripts/` | agent/internal tool surface | Layer 2 tools + maintainer/debug scripts incl. `hldspec_agent_session.py`, `check_product_readiness.sh`. Do not move in this plan. |
| `tests_v2/` | test root — primary | Full validation suite + anti-drift contracts (Layer 7). Do not move. |
| `tests/` | test root — V1 integration | Script-level integration incl. V1-pipeline coverage. Do not move. |
| `tests_legacy/` | test root — legacy/reference | Reference-only; do not delete without a same-commit V2 replacement. |
| `docs/` | docs | Active docs, `docs/archive/` history. Canonical: `HLDSPEC_TERMINOLOGY_AND_FLOW.md`. |
| `poc/` | compatibility/PoC | Proof-of-concept runner over the V1 pipeline. |
| `templates/` | templates | Orchestrator instruction templates. |
| `.claude/` | repo meta | Tooling config. |

## What should not move yet

- `hldspec/`, `scripts/`, `tests_v2/`, `tests/`, `tests_legacy/` — active source
  and test roots; moving them now would break imports and the readiness gate.
- V1 compatibility files (`hld_spec_sync.py`, `hld_spec_downstream.py`,
  `hld_map.py`) — still wired; isolate only in Phase 5 after callers are proven.

## What may move later

- `Dev`, `TERMINOLOGY.md` and other doc/pointer files with no code references —
  Phase 4, low-risk.
- V1 surfaces into a clearly fenced location — Phase 5, after references proven.

## What must stay for compatibility

- `hld_map.py` stays at the root: it is the shared parser imported by both V2 and
  V1.
- The V1 pipeline files stay until every caller is migrated; they are labeled
  compatibility/V1, never deleted by this plan.

## How anti-drift tests prevent repeat drift

`tests_v2/` binds the intended shape to executable checks: the command surface to
the real parser, the public UX to the agent one-liner, the terminology to the
canonical doc, the repo layout to `REPO_LAYOUT.md`, and (this plan) the layer map
and migration phases to `tests_v2/test_architecture_layers_contract.py`. A future
change that reintroduces script-first UX, collapses journeys and modes, claims
production-ready, or calls V1/compatibility "active V2 core" fails a test before
it can land.
