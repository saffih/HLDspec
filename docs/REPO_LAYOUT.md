# HLDspec Repository Layout

A compact map of what lives at the repo root and which things are active,
shared, V1-pipeline, historical, or pointers. When a file's purpose is unclear,
start here. For the doc-by-doc index see [`DOCS_INDEX.md`](DOCS_INDEX.md).

> Note: this describes the **HLDspec repo itself**, not a generated target
> workspace. Target-workspace layout is in [`../README.md`](../README.md).

## Active V2 source and entrypoints

| Path | Role |
|---|---|
| `hldspec/` | Active V2 source: state machines, contracts, renderers, operator state, readiness. |
| `scripts/hldspec_agent_session.py` | Public agent-first facade (`start`/`status`/`review`/`continue`/`diff`/`doctor`/`speckit-doctor`/`operator-state`/`speckit-state`/`git-lifecycle`). |
| `scripts/hldspec_v2.py` | V2 CLI entry point. |
| `scripts/hldspec_smoke_slice_e2e.py` | Deterministic source-package/mirror/anchor/slice smoke. |
| `scripts/check_product_readiness.sh` | Reproducible local product-readiness check (focused tests + full `tests_v2` + smoke). |

## Shared parser

| Path | Role |
|---|---|
| `hld_map.py` | **Shared** HLD-format **parser** (sections, metadata, refs, cycles). Imported by both the V2 module (`hldspec/hld_marking.py`) and the V1 pipeline. Not legacy — do not remove. |

## V1 HLD→SpecKit pipeline (still wired, not dead)

| Path | Role |
|---|---|
| `hld_spec_sync.py` | **V1** pipeline: sync one HLD into constitution + native SpecKit specs + `.specify/sync/` reports. Still invoked by `scripts/first_run_readonly.sh`, `scripts/full_cycle_smoke.sh`, and `tests/`. |
| `hld_spec_downstream.py` | **V1** pipeline: continue after sync to produce downstream SpecKit artifacts (plan/research/tasks/contracts). Invoked by `poc/run_poc.sh`. |

These predate the V2 `hldspec/` machine flow. They remain because read-only
first-run analysis and the PoC still call them. Treat them as V1 surface; new
work belongs in `hldspec/` and `scripts/hldspec_agent_session.py`.

## Root docs

| Path | Role |
|---|---|
| `README.md` | Conceptual front door + public command surface + quickstart. |
| `AGENTS.md` | Agent bootstrap and hard rules. |
| `CLAUDE.md` | Session bootstrap / project reference. |
| `TASKS.md` | Living P0/P1/P2 task list. |
| `Dev` | **Session-restart pointer** (markdown). Says: read `CLAUDE.md`, then `TASKS.md`, then `AGENTS.md`. Low-readability filename kept for continuity; nothing in active code references it (only `docs/archive/`). |
| `HLD_FORMAT.md` | Reference: the grepable HLD input format consumed by the V1 pipeline. |
| `HLD_GENERATION.md` | Reference: how to author/convert an HLD into that format. |
| `TERMINOLOGY.md` | Older root glossary. The authoritative terminology source is `docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md`, which wins on any conflict. |
| `LICENSE` | License. |

## Test roots

| Path | Role |
|---|---|
| `tests_v2/` | **Primary** full validation suite — machine contracts, behavior, negative paths, docs/anti-drift contracts. The required full-suite gate (`python3 -m unittest discover -s tests_v2`). |
| `tests/` | Active script-level integration tests (includes V1-pipeline coverage). |
| `tests_legacy/` | Reference-only legacy tests. Do not delete without a same-commit V2 replacement. |

## Other directories

| Path | Role |
|---|---|
| `docs/` | Active docs, this layout map, and `docs/archive/` historical records. |
| `poc/` | Proof-of-concept runner over the V1 pipeline. |
| `templates/` | Orchestrator instruction templates. |
