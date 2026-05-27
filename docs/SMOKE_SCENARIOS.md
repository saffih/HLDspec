# HLDspec Smoke Scenarios

## Purpose

Smoke scenarios are deterministic, self-contained end-to-end checks that prove
a specific HLDspec pipeline path works without requiring a real HLD project,
agents, or SpecKit invocation. Each scenario creates its own temp workspace,
runs real production code, validates the output, and reports PASS or FAIL.

---

## Scenario: slice-controlled source package (3-anchor HLD)

**Script:** `scripts/hldspec_smoke_slice_e2e.py`
**Test:** `tests_v2/test_hldspec_smoke_slice_e2e.py`
**Fixtures:**

```text
tests_v2/fixtures/tiny_smoke_HLD.md
tests_v2/fixtures/bad_smoke_HLD_missing_anchor.md
tests_v2/fixtures/expected_smoke_artifacts.txt
```

Proves the local source-package build pipeline works on a minimal 3-anchor HLD:

```
HLD-001  Product Goal
HLD-002  Domain Behavior
HLD-003  Interface
```

The smoke is deterministic and local. It does not spawn Claude, Codex, Devin, or
SpecKit.

### Workspace layout

Each default run creates:

```text
/tmp/hldspec-smoke-XXXXXX/
  tiny_HLD.md
  target/
    .hldspec/source_package/
    .specify/source/
```

All generated artifacts stay under `target/`. The copied source HLD is the only
file outside `target/` in the temp root.

### What it validates

| Check | Detail |
|---|---|
| Expected artifact manifest | Every path in `tests_v2/fixtures/expected_smoke_artifacts.txt` exists under `target/` |
| Source package files | `.hldspec/source_package/` exists and contains the source package artifacts |
| SpecKit mirror files | `.specify/source/` exists and contains the derived mirror artifacts |
| Reference map anchors | HLD-001, HLD-002, HLD-003 each appear in `hld_reference_map.json` |
| Single spec input citations | HLD-001, HLD-002, HLD-003 each cited in `speckit_single_spec_input.md` |
| Slice policy | If slice policy artifacts are present, `implementation_slices.json` is valid and the policy states one specify/plan/tasks/analyze flow with controlled implementation passes |
| Mirror banner | `.specify/source/HLD.md` carries the GENERATED banner |
| Idempotency | Running the build twice produces the same result |
| Negative fixture | `bad_smoke_HLD_missing_anchor.md` fails because HLD-003 is absent |

### Usage

```bash
# Run once, clean up temp dir on exit.
python3 scripts/hldspec_smoke_slice_e2e.py

# Keep the temp dir for inspection.
python3 scripts/hldspec_smoke_slice_e2e.py --keep

# Use a specific temp root.
python3 scripts/hldspec_smoke_slice_e2e.py --root /tmp/hldspec-smoke-manual --keep

# Emit a JSON summary before the final result line.
python3 scripts/hldspec_smoke_slice_e2e.py --json

# Create a tmux visibility session (skipped if tmux absent).
python3 scripts/hldspec_smoke_slice_e2e.py --tmux

# Create and attach to the tmux session.
python3 scripts/hldspec_smoke_slice_e2e.py --tmux --attach

# Prove the negative fixture fails.
python3 scripts/hldspec_smoke_slice_e2e.py --hld tests_v2/fixtures/bad_smoke_HLD_missing_anchor.md
```

### Output contract

For normal non-JSON runs, stdout is exactly one of:

```
HLDSPEC_SMOKE_RESULT: PASS
HLDSPEC_SMOKE_RESULT: FAIL
```

For `--json`, stdout contains the JSON summary followed by the same final result
line. Failure details are written to stderr.

Exit code 0 on PASS, 1 on FAIL.

### What it does NOT do

- Does not invoke Claude, Codex, Devin, or any uncontrolled agent.
- Does not run SpecKit (`specify init` / `specify run`).
- Does not modify any source HLD.
- Tmux is a visibility window only. If tmux is absent the run reports `SKIP_TMUX` to stderr and continues.

---

## Adding a new scenario

1. Write `scripts/hldspec_smoke_<name>.py` with `run_smoke(target) -> (bool, list[str])` and a `main()` that prints `HLDSPEC_SMOKE_RESULT: PASS/FAIL` as the last line.
2. Write `tests_v2/test_hldspec_smoke_<name>.py` with direct unit tests and a subprocess test for the output contract.
3. Add an entry to this file and to `docs/DOCS_INDEX.md`.
