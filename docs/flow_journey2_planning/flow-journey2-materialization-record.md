# Flow Journey 2 — Materialization Record

Date: 2026-07-04
Authorization: `FLOW_JOURNEY_2_MATERIALIZATION_AUTHORIZATION` /
`AUTHORIZE_MATERIALIZATION_BUILD_SLICE: yes` — Hadas / project owner.
Inputs: approved planning package (PR #127) + package-level approval (PR #128).
Machine receipt: `flow-journey2-materialization-receipt.json` (same directory).

---

## Placement decision

The authorization allows writing `.hldspec/source_package/`. Flow carries an
untracked `.hldspec-run.json` controller pointer, and HLDspec's own path
resolution (`hld_source_package.source_package_paths` →
`control_paths.resolve_controller_root`) makes the authoritative location:

```
/Users/saffi/code/flow/.hldspec-runs/flow-6f7f768dd575-12473df618d3/.hldspec/source_package/
```

Writing at the literal target root while that pointer is live would create a
fail-closed `source_package_split_brain`. Materialization therefore wrote to
the pointer-resolved directory — the system-conformant reading of the
authorized path. No pointer file was created, edited, or deleted. The
target-root-vs-run-dir placement question remains the known open design
CONFLICT (Journey 3 dogfood) and is not decided by this record.

## What was written (all inside the resolved `source_package/` only)

| File | Role |
|---|---|
| `HLD.md` | byte-identical copy of flow's live HLD (SHA-256 `3c376ae9…f5d0`) |
| `HLD.marked.md` | derived, `<!-- ANCHOR: HLD-NNN -->` markers, 17 anchors |
| `hld_reference_map.json` | derived anchor map, 17 anchors, integrity errors: none |
| `speckit_single_spec_input.md` | curated copy (PR #127), byte-identical |
| `engineering_guidelines.md` | curated copy, byte-identical |
| `constitution.proposed.md` | curated copy (proposal-only), byte-identical |
| `architecture_package.json` | curated copy, byte-identical |
| `feature_dependency_graph.json` | curated copy; no manifest slot — SHA-256 `41211f43…f47fb4` recorded here |
| `speckit_invocation_queue.json` | curated copy; no manifest slot — SHA-256 `d66828a4…028854` recorded here |
| `source_manifest.json` | generated last; per-file SHA-256 over authoritative slots |
| `source_package.json` | generated last; binding: `target_path=/Users/saffi/code/flow`, `source_sha256=3c376ae9…f5d0`, state `SOURCE_PACKAGE_IMPORTED`, NOT UNBOUND_LEGACY |

## Verification

- `validate_source_package`: ok=true (missing=[], hash_mismatches=[],
  semantic_errors=[]). Standalone structural validation only — this is NOT
  SOURCE_PACKAGE_APPROVAL_GATE, which was not run.
- Anchor claims: 75 requirements, each cites ≥1 valid anchor, all within the
  11 decomposable sections; 0 unknown anchors. Checked with a
  format-equivalent semantic validator; the literal
  `find_unsupported_claims` enforces the machine-generated prefix layout and
  flags the curated trailing-citation format (0 unknown-anchor flags) — both
  outputs preserved in the machine receipt.
- Flow no-mutation outside allowed path: `HLD.md` SHA-256 identical before
  and after; `git status --short` delta none (writes are inside the
  already-untracked `.hldspec-runs/`); `.specify/source/` mirror NOT written
  (mtimes untouched since Jun 7–8); flow tests 66 passed after.
- Preserved: 11/6 split, all 6 provisional revisit triggers, HLD-017
  candidate-only boundary, J0-12 not globally closed (curated files are
  byte-identical to the approved package, so all PR #127 statements carry).

## Open blocker — pointer BOUND_MISMATCH

`journey3-status` (read-only) reports phase READY_FOR_SPECKIT_SPECIFY but
verdict BLOCKED with `binding_status=BOUND_MISMATCH`: the pre-existing
target-root `.hldspec-run.json` pointer still records the phantom-era
`source_sha256=12473df6…`, while the fresh package binding records the true
`3c376ae9…f5d0`. The pointer is a target-root control file outside this
slice's authorized write paths, so it was deliberately not modified.
Resolving it requires a separate explicit owner authorization to update (or
regenerate) `.hldspec-run.json` with the correct source hash.

## Known residuals

1. Stale Jun-29 phantom-era artifacts remain in the package directory
   (runbook, runner/consultant prompts, slicing templates, session_plan.json,
   subagent_packets/, anchor_coverage_schema.json). Deletion was not
   authorized. Where those files occupy manifest slots, the fresh manifest
   hashes their stale content — validation passes structurally, but their
   content predates the approved package. Regenerate-or-remove is a
   follow-up decision (bundle with the pointer fix).
2. Before-state fidelity: two aborted driver runs overwrote the receipt's
   pristine hashes for 5 of the 24 pre-existing stale files (HLD.md,
   HLD.marked.md, hld_reference_map.json, engineering_guidelines.md,
   speckit_single_spec_input.md). The other 19 pristine hashes, including
   the stale manifest/binding pair, are preserved. No unauthorized writes
   occurred at any point.
3. `feature_dependency_graph.json` / `speckit_invocation_queue.json` have no
   slot in the code's manifest schema (contract/code gap) — this record and
   the machine receipt are the compensating traceability.

## Not done (per NOT_AUTHORIZED)

No SOURCE_PACKAGE_APPROVAL_GATE. No SpecKit. No command wiring. No
Journey 3. No feature implementation. No implementation backlog. No HLD-017
commitments. No writes outside the resolved `source_package/` directory.
No git commits in flow.

## Required next approvals

1. Owner authorization to fix the `.hldspec-run.json` pointer
   (`source_sha256` → `3c376ae9…f5d0`) — clears BOUND_MISMATCH; optionally
   bundle stale-artifact cleanup/regeneration in the same slice.
   RunSkeptic caveat for that slice: the run-dir name embeds the phantom
   hash prefix (`…-12473df618d3`, from `run_state.run_id_for_target`);
   pointer resolution reads `controller_root` verbatim, so a sha-only fix
   keeps the package reachable, but any path that re-derives the run root
   from the corrected hash would compute `…-3c376ae99170` and could orphan
   this package — verify before executing.
2. SOURCE_PACKAGE_APPROVAL_GATE run (requires RunSkeptic + Consultant PASS +
   human approval) — after 1.
3. CONSTITUTION_APPROVAL_GATE before `constitution.proposed.md` is applied.
4. SPECKIT_PREWORK_APPROVAL_GATE before any SpecKit invocation.
5. Helper selection (Journey 3 decision).
