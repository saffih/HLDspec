# HLDspec Smoke Scenarios

## Purpose

Smoke scenarios are deterministic local checks for the real HLDspec workflow. They are small enough to debug and strict enough to catch broken source-package, mirror, anchor, and slice-artifact behavior early.

## Smoke 1: source package, mirror, anchors, and slice artifacts

Command:

```bash
python3 scripts/hldspec_smoke_slice_e2e.py --keep
```

Machine-readable output:

```bash
python3 scripts/hldspec_smoke_slice_e2e.py --json --keep
```

Optional visibility surface:

```bash
python3 scripts/hldspec_smoke_slice_e2e.py --tmux --keep
```

Tmux is optional UI only. If tmux is unavailable, the smoke reports `SKIP_TMUX`; this is not a failure.

## Destination layout

The smoke creates a temp root such as:

```text
/tmp/hldspec-smoke-XXXXXX/
  tiny_HLD.md
  target/
    targetHLD/
    .hldspec/source_package/
    .specify/source/
```

The destination target is always:

```text
<temp_root>/target
```

Generated target artifacts must stay under the temp target. The HLDspec repo must not receive generated target artifacts.

## What Smoke 1 proves

- `scripts/hldspec_agent_session.py start` can prepare a target.
- `hldspec.hld_source_package.build_source_package_content` can build source-package content.
- Journey 3 mediator guidance artifacts are materialized in the target workspace:
  - `.hldspec/mediator/mediator_packet.json`
  - `prompts/mediator/START_MEDIATOR.md`
  - `prompts/mediator/DEVIN_MEDIATOR_SKILL.md`
  - `prompts/mediator/CODEX_CLAUDE_MEDIATOR.md`
- `.hldspec/source_package/` contains the expected HLD, anchor, manifest, single SpecKit input, and slice files.
- `.specify/source/` receives a generated read-only mirror.
- `HLD.marked.md` contains anchors for `HLD-001`, `HLD-002`, and `HLD-003`.
- `hld_reference_map.json` contains the same anchors.
- `speckit_single_spec_input.md` cites those anchors.
- Slice artifacts use the real generated filenames:
  - `implementation_slicing_policy.md`
  - `implementation_slices.json`
  - `slice_test_policy.md`
  - `speckit_slice_execution_prompt.md`
  - `anchor_coverage_schema.json`

## What Smoke 1 does not prove

- It does not run real SpecKit implementation.
- It does not spawn Claude, Codex, Devin, or uncontrolled agents.
- It does not prove a production app works.
- It does not make tmux an approval source.

## Output contract

The final output includes exactly one result line:

```text
HLDSPEC_SMOKE_RESULT: PASS
```

or:

```text
HLDSPEC_SMOKE_RESULT: FAIL
```

The output also prints:

```text
source_hld:
target_dir:
source_package:
specify_source:
tmux:
checks_passed:
checks_failed:
```

On failure, output includes:

```text
failed_check:
details:
next_action:
```

## Troubleshooting

Use `--keep` to preserve the target for inspection. On failure, the target is preserved automatically.
