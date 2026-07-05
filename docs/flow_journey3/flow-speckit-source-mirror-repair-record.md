# Flow SpecKit Source-Mirror Repair — Record

Date: 2026-07-05
Run: FLOW_SPECKIT_SOURCE_MIRROR_REPAIR (clean-room, TOUGHNESS HIGH)

## Purpose

Repair the fail-closed blocker found before the first controlled
`/speckit.specify`: the generated read-only mirror `flow/.specify/source/`
had drifted from the approved source package, and pre-specify readiness
validation did not detect it.

## Authorization

FLOW_SPECKIT_SOURCE_MIRROR_REPAIR_AUTHORIZATION — Hadas / project owner.
Scope: mirror re-materialisation + validator hardening only. No SpecKit
invocation, no `/speckit.specify` retry, no Journey 3 execution.

## Clean-room proof

All facts re-derived from current disk/git/command output this run. Prior
chat, memory, and the prior handoff were treated as data, not evidence. No
load-bearing claim remained unverified.

## Re-verified blocker

- Gate basis re-verified: PR #132, #133, #134 MERGED on HLDspec main
  (e4d38ab / d60d080 / d4b62c0), each record states PASSED.
- Approved package `speckit_single_spec_input.md`
  sha256 `7cc8395a7333ba9819e977bdd24efd94d2d7f896878a4c54dd8aeff8aed5494e`
  — contains FLOW-F01.
- Stale mirror copy sha256
  `bf9784f0cae9a708cf3d9ad30f93c4262f64e93157b3d9d1bf56f81eb1832448`
  — zero FLOW-F01 occurrences (pre-decomposition Jun-7 snapshot).
- Full scan (Worker B): 12 of 14 mirror files drifted from their package
  counterparts; 2 matched byte-for-byte; no materialisation receipt existed.
- `journey3-status` reported READY_FOR_SPECKIT_SPECIFY with validation ok —
  confirming the validation gap.

## Repair

Re-materialised via the repo-supported mechanism
`hldspec.hld_source_package.materialize_specify_mirror(source_dir, mirror_dir)`
(GENERATED banner + package bytes for `.md`, byte-identical copy otherwise)
— not a hand copy, and deliberately not a plain byte-copy, because the
banner is part of the repo's mirror contract. 14 files written; post-repair
verification (Worker D): 14/14 match contract-expected content; FLOW-F01
present; repaired mirror input sha256
`78e3c483873865153d8b535c4c435ce097652df74315ab6e102440d0d77f85b9`.

Source package unchanged before/after: manifest hash
`527141c728c485e7a13a4dc78ecfe3efc4818dd95e581dae6870b312bb477403` (24 files).

## Flow PR

- flow PR #16 "docs: refresh SpecKit source mirror from approved package"
  — MERGED, merge commit `f39916c` (2026-07-05), 14 files, +2264/-0.
- Mirror files force-added past the `/.specify/` gitignore so future drift
  is reviewable (tracked-constitution precedent, flow PR #15).
- Post-merge hash re-verified on flow main.

## Validator owner

Pre-specify readiness path (identified by Worker E):
`scripts/hldspec_agent_session.py:command_journey3_status`
→ `next_feature_readiness.build_next_feature_readiness_report` (phase)
→ `journey3_driver.build_journey3_status` (driver verdict)
→ `hld_source_package.validate_source_package` (package-only; never saw the
mirror — `build_journey3_status` resolved the mirror path and discarded it).

## Validation hardening

- `hld_source_package.mirror_freshness_blockers(source_dir, mirror_dir)`:
  every `MIRROR_FILES` entry present in the package must exist in the mirror
  with exactly the content `materialize_specify_mirror` would write
  (banner-normalised for `.md`); lingering HLDspec-managed orphans block;
  non-HLDspec files in the mirror are never judged. Shared content rule
  extracted to `_expected_mirror_text` so writer and checker cannot diverge.
- `journey3_driver.build_journey3_status`: mirror blockers fail the driver
  closed (BLOCKED) and are exposed as
  `source_package_validation.mirror_stale`; fresh mirror recorded as
  evidence `specify mirror fresh`. Duplicate blockers (driver + injected
  phase) deduped, first occurrence kept.
- `next_feature_readiness`: new phase `SOURCE_MIRROR_STALE` (SAFETY_BLOCKED)
  replaces both `READY_FOR_SPECKIT_SPECIFY` exits when a target with an
  authoritative source package has a stale/missing mirror; package-less
  targets are exempt. READY_FOR_SPECKIT_SPECIFY can no longer be reported
  over a stale required mirror.

## Tests

- New: 5 freshness-contract tests (`tests_v2/test_source_package.py`),
  3 driver tests incl. dedupe (`tests_v2/test_journey3_driver.py`),
  2 phase-gating tests (`tests_v2/test_next_feature_readiness.py`).
- Suites: tests_v2 2406 passed; tests 173 passed; flow 66 passed.
- Live probes on real flow target (Worker F, transient with exact git
  restore, before/after sha `78e3c483…` verified): stale content → BLOCKED
  `SOURCE_MIRROR_STALE`; missing mirror file → BLOCKED; unrelated file in
  mirror dir → ignored; restored fresh state → READY_FOR_SPECKIT_SPECIFY.

## Hidden/bidi scan

CLEAN on all 14 repaired flow mirror files and on the changed HLDspec
files + this record (no bidi controls, no hidden control characters).

## RunSkeptic

Verdict recorded in the final run receipt; run against fresh
`saffih/skeptic/main/skeptic.md` covering: blocker re-verification, repair
from approved package (not invented), no source-package mutation, no
product/runtime mutation, no SpecKit invocation, validator wired into the
real readiness path, Flow-before-HLDspec merge order, context protection.

## Boundaries preserved

- SpecKit was not invoked. `/speckit.specify` was not run or retried.
- Journey 3 was not started.
- Flow product/runtime files were not modified (HLD.md, README.md, core.md,
  flow.py, test_flow.py sha-verified unchanged).
- Source package files were not modified (manifest hash identical).
- Mirror was repaired from the approved package source.
- Validation now blocks stale required mirrors before `/speckit.specify`.
- HLD-017 candidates remain candidates only.
- J0-12 was not globally closed.

## Next action

Owner may separately re-authorize the first controlled `/speckit.specify`
in a fresh clean-room session; the previous specify authorization was
consumed by its fail-closed stop. Nothing in this record authorizes SpecKit
execution.
