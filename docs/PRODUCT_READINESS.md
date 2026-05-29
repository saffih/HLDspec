# HLDspec Product Readiness

A scorecard of where HLDspec stands against three readiness tiers, with the
evidence behind each call. It is honest by design: **a tier is YES only when its
gates are actually met.** Production-ready overclaiming is forbidden.

Status date: 2026-05-29. Re-run the evidence commands before trusting it.

## Tiers and gates

### Supervised MVP — status: YES

A knowledgeable operator can run a command, see state, and get an
evidence-backed next safe action.

| Gate | Met | Evidence |
|---|---|---|
| Operator State implemented, bounded to readiness scope | YES | `hldspec/speckit_operator_state.py`; `tests_v2/test_speckit_operator_state.py` |
| `next_safe_action` is evidence-backed | YES | report `evidence` + `source_facts_used`; operator-state tests |
| CLI exposes current state + next safe action | YES | `operator-state` / `speckit-state` in `scripts/hldspec_agent_session.py` |
| Tests cover the command path | YES | `test_cli_operator_state_prints_summary` |
| Docs are not misleading | YES | command surface + boundaries in `README.md`, terminology/anti-drift tests |
| Full `tests_v2` passes | YES | `python3 -m unittest discover -s tests_v2 -v` passes |
| Smoke passes | YES | `python3 scripts/hldspec_smoke_slice_e2e.py --json` reports `HLDSPEC_SMOKE_RESULT: PASS` |
| Known limitations explicit | YES | this file + README boundaries |
| No known P0 ACTION/CONFLICT | YES | — |

### Standalone user — status: YES (with the docs in this branch)

A new user with no project history can orient and run one validation command.

| Gate | Met | Evidence |
|---|---|---|
| README quickstart for a new user | YES | README "Main user workflow" |
| Public command surface documented | YES | README command-surface table; `test_product_readiness_docs` binds it to `build_parser()` |
| start/status/doctor/speckit-doctor/operator-state/speckit-state roles explained | YES | README command-surface table |
| PASS/ACTION/CONFLICT explained | YES | README "Reading results" table |
| Failure messages tell what to do next | YES | `next_safe_action` on every operator-state result |
| Repo layout understandable | YES | `docs/REPO_LAYOUT.md` |
| Active vs legacy vs compatibility files clear | YES | `docs/REPO_LAYOUT.md` |
| ≥1 sample/demo/smoke documented | YES | `docs/SMOKE_SCENARIOS.md` |
| One validation command without project history | YES | `scripts/check_product_readiness.sh` |
| No known P1 ACTION/CONFLICT | YES | command-surface drift resolved: `HLDSPEC_TERMINOLOGY_AND_FLOW.md` is the single canonical surface; README, `USER_RUN_MODEL.md`, and `HLDSPEC_USE_CASES_AND_API.md` defer to it and list all 9 commands |

### Production — status: NO

Not production-ready. The following gates are not met.

| Gate | Met | Blocker |
|---|---|---|
| Install/release story | NO | no `pyproject.toml`/`setup`/packaged release; run from a clone only |
| Reproducible release check or CI | PARTIAL | `.github/workflows/product-readiness.yml` runs `scripts/check_product_readiness.sh` on `pull_request` and `push` to `main` with Python 3.10; release/install story still absent |
| Stable public command surface | PARTIAL | surface is documented but not version-frozen or deprecation-policed |
| Recovery/rollback docs | PARTIAL | path-safety summarized below; no full recovery/rollback runbook |
| Security/path-safety review | PARTIAL | reviewed (below); no independent security sign-off |
| Multiple real HLD pilots | NO | only the deterministic smoke fixture; no documented external pilots |
| No independent RunSkeptic blocker | UNKNOWN | needs an independent RunSkeptic pass on this branch |

**Production-ready: NO** until every production gate above is met and verified.

CI uses Python 3.10 because the core `hld_spec_sync.py` and `hld_spec_downstream.py`
scripts declare `requires-python = ">=3.10"` and the local compatibility check
for this slice did not find a lower supported version to target.

## Path safety and recovery (review summary)

Reviewed read-only; no code defect found. Posture today:

- Target workspaces are user-chosen directories; HLDspec works on workspace
  copies and treats the source HLD as read-only.
- The V1 downstream/sync writers refuse writes outside the workspace, refuse
  protected paths (`.git`, `.agents`, `.codex`, `logs`, `.speckit*`), and
  constrain implementation writes to explicit `--implementation-root` paths
  (`hld_spec_downstream.validate_write_target`, `hld_spec_sync.is_sync_allowed_path`).
- The smoke asserts no repo pollution (generated artifacts stay under a temp
  target).
- Recovery today: re-run `operator-state` / `speckit-doctor`; they are
  read-only and idempotent and print the next safe action. A failed check does
  not leave partial state in the repo.

Not yet covered: a full recovery/rollback runbook for a partially-built target
workspace. Tracked as production-tier work.

## What independent RunSkeptic must verify

- The command-surface documentation matches the real parser (the test binds to
  `build_parser()`, but RunSkeptic should confirm the test is the real gate).
- `operator-state` `next_safe_action` is genuinely evidence-backed across the
  PASS/ACTION/CONFLICT branches, not just present.
- The Operator / Doctor / Devin Mediator boundary is not weakened by the new
  docs.
- The "Standalone user: YES" call is justified and not overclaiming, and
  "Production: NO" is preserved.
- The command surface is reconciled to one canonical source
  (`HLDSPEC_TERMINOLOGY_AND_FLOW.md`); confirm no doc reintroduces a competing
  "canonical" command list.

## Re-run the evidence

```bash
scripts/check_product_readiness.sh
```

This runs the focused Operator State / readiness / anti-drift / terminology /
product-readiness / repo-layout tests, the full `tests_v2` suite, and the smoke.
