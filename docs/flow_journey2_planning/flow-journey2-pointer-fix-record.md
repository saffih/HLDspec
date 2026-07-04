# Flow Journey 2 — Pointer Fix Record

Date: 2026-07-04
Authorization: `FLOW_POINTER_FIX_AUTHORIZATION` / `AUTHORIZE_POINTER_FIX_SLICE: yes`
— Hadas / project owner.
Precondition: materialized bound package (PR #129 record), journey3-status
BLOCKED / `BOUND_MISMATCH`.

---

## Run-dir-name caveat verification (required before any write)

Verified read-only against HLDspec code before editing:

- The BOUND_MISMATCH comparison reads exactly one pointer field:
  `source_sha256` (`target_discovery.py` `_source_package_binding`, pointer
  vs package binding).
- `run_id_for_target` (which embeds the hash prefix in the run-dir name) has
  exactly one caller chain — `external_run_root` → `command_start` —
  creation-time only. Every resolution-time path
  (`control_paths.resolve_controller_root`, `source_package_paths`,
  `source_freshness`, readiness/status paths) reads the pointer's
  `controller_root` verbatim and never re-derives it from the sha. No code
  compares the run-dir name to any sha.
- Verdict: a sha-only pointer edit cannot re-derive a different run root;
  the materialized package at `…-12473df618d3/` stays reachable. (A future
  `hldspec start` would mint a NEW run dir — a new run, not an orphaning of
  this fix.)
- Truthfulness check: live `/Users/saffi/code/flow/HLD.md` was re-hashed
  immediately before the write and equals `3c376ae9…f5d0`.

## The edit

One file: `/Users/saffi/code/flow/.hldspec-run.json`. Field-level diff:

| Field | Before | After |
|---|---|---|
| `source_sha256` | `12473df618d3ebe0b1411ee54e50b858993137a3c1c173b8cfa65df1481930b5` (phantom-era) | `3c376ae9917b05d09d71fd73037b41a800eecbe51eaa5167481f1db11cf7e5d0` (true) |
| `created_or_updated_at` | `2026-06-07T19:09:44+00:00` | `2026-07-04` update timestamp |

All other fields unchanged, including `controller_root`
(`…/.hldspec-runs/flow-6f7f768dd575-12473df618d3`). File re-serialized
(stable key order); whole-file SHA-256 before
`35bad53bc5ddd60d24f7472ceb050a61b3198b5b4c7cc298b7400149817428df`, after
`167397163862c370a6fcd4d0a05711a05aa3e87db50c58711cf4b8a37cec83ce`.

## Stale-artifact cleanup decision: none

- The Jun-29 files in the source-package dir are manifest-hashed; deleting
  any of them breaks `validate_source_package` until a manifest re-run, and
  their content is deterministic template output. KEEP.
- `session_plan.json` + `subagent_packets/` are mechanically removable
  (journey3-status phase does not derive from them), but removal flips
  continue-preflight gating from gated to legacy OFF — a behavioral
  tradeoff for the owner, not a proven-safe cleanup. KEEP, deferred.

## Escalated recurrence vector (not fixed — outside allowed paths)

`…-12473df618d3/.hldspec/agent_session.json` still records the phantom
`source.sha256`. Consequences if left: `detect_mode` keeps reporting
"update", and a future build-loop continue would rebuild the package
binding with the phantom sha, re-creating BOUND_MISMATCH against the
corrected pointer. That file lives in the controller root's `.hldspec/`,
not in the two authorized write paths, so it was deliberately not modified.
Fix (one field) requires separate owner authorization — recommended before
or bundled with the SOURCE_PACKAGE_APPROVAL_GATE slice.

## Verification after the edit

- `journey3-status` (read-only): `binding_status: BOUND_MATCH`,
  `source_package_validation: ok=True`,
  `journey3_phase: READY_FOR_SPECKIT_SPECIFY`.
- `HLD.md` SHA-256 unchanged (`3c376ae9…f5d0`); no product/runtime file
  touched (HLD.md, README.md, core.md, flow.py, test_flow.py all untouched).
- Flow `git status --short` category unchanged (pointer remains untracked).
- Flow tests: 66 passed.

## Not done (per NOT_AUTHORIZED)

No SOURCE_PACKAGE_APPROVAL_GATE. No SpecKit. No command wiring. No
Journey 3. No implementation backlog. No HLD-017 commitments. No global
J0-12 closure.

## Required next approvals

1. Owner authorization to correct `agent_session.json` `source.sha256`
   (recurrence vector above) — one field, same rationale as this slice.
2. SOURCE_PACKAGE_APPROVAL_GATE run (RunSkeptic + Consultant PASS + human
   approval).
3. CONSTITUTION_APPROVAL_GATE, then SPECKIT_PREWORK_APPROVAL_GATE, then
   helper selection — unchanged from the materialization record.
