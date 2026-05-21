# HLD Spec Kit tools

Tools for turning one large HLD into native Spec Kit artifacts and continuing downstream toward implementation closure.

## Install

```bash
chmod +x hld_spec_sync.py
chmod +x hld_spec_downstream.py
```

## Operating rules, terminology, and target constitution

HLDspec operating rules live in [AGENTS.md](AGENTS.md).

Canonical names are defined in [TERMINOLOGY.md](TERMINOLOGY.md).

Important distinction:

- HLDspec repo operating rules are not `.specify/memory/constitution.md`.
- `.specify/memory/constitution.md` is the target Spec Kit Constitution inside the workspace being processed.
- `hld_spec_sync.py` should create, update, leave unchanged, or report conflict for the target Spec Kit Constitution during sync.

Key rules:

- HLDspec uses the real Skeptic Framework from `https://github.com/saffih/skeptic/blob/main/skeptic.md`.
- A Beskeptic Cycle is HLDspec's operational use of the real Skeptic flow on selected Key Aspects.
- HLD Sections are design source units, not specs.
- Specs are capability units.
- Specs must be planned bottom-up with a Spec Build Plan before multi-spec work.
- Coverage Gates and Integration Gates are required before downstream work.
- API contracts, performance, memory, dependencies, data/state ownership, and reliability are first-class Key Aspects when relevant.


## HLD input format

For large HLDs, prefer one canonical `HLD.md` with stable, grepable section metadata instead of many manually maintained HLD source files.

Recommended section format:

```md
## HLD-003 - Sync Engine

HLD-ID: HLD-003
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: 001,002
HLD-RESOURCES: hld_spec_sync.py,.specify/memory/constitution.md,specs/*/spec.md
HLD-VERIFY: related specs preserve HLD anchors; feature graph includes dependencies
```

Use inline references for section relationships:

```md
This section DEPENDS REF HLD-002 because source-of-truth rules define what may be generated.
This section REF HLD-006 for rollback behavior.
```

This is a short excerpt; a complete HLD defines referenced sections or marks unknown references as `TBD` nearby.

See:

- [HLD_FORMAT.md](HLD_FORMAT.md) for the HLD section format and grep/reference rules.
- [HLD_GENERATION.md](HLD_GENERATION.md) for a reusable prompt to create HLDs in this format.
- [HLD_DOCS_JUDGE_WORKFLOW.md](HLD_DOCS_JUDGE_WORKFLOW.md) for an optional Skeptic-derived Judge workflow for documentation-project HLDs.

## Agent usage

For agent-facing repository instructions, see [AGENTS.md](AGENTS.md).

Agents should use the wrapper scripts instead of manually editing generated Spec Kit artifacts.

## Sync script

`hld_spec_sync.py` syncs one large HLD into a Spec Kit-native constitution, feature specs, sync index, graph, and reports.

The sync script only accepts `WRITE FILE` targets for `.specify/memory/constitution.md`, `.specify/sync/**`, and `specs/<NNN-feature-slug>/spec.md`. Agent output that tries to write implementation files or protected paths fails the run.

## Default Devin run

```bash
./hld_spec_sync.py --hld ./hld.md
```

The default agent is Devin, and its default model is `swe-1.6`.

## Greenfield

```bash
./hld_spec_sync.py --hld ./hld.md --mode greenfield
```

Greenfield compares the HLD desired state against an empty current state.

## Brownfield

```bash
./hld_spec_sync.py --hld ./hld.md --mode brownfield
```

Brownfield compares the HLD desired state against existing constitution, native Spec Kit specs, and `.specify/sync/` metadata.

## Auto mode

```bash
./hld_spec_sync.py --hld ./hld.md
```

Auto mode uses brownfield if `specs/*/spec.md` exists, otherwise greenfield.

## Layout contract

Generated feature specs are native Spec Kit specs and live in the standard Spec Kit feature directory:

```text
specs/<NNN-feature-slug>/spec.md
```

HLD sync metadata is kept out of `specs/` so the `specs/` directory remains compatible with Spec Kit workflows:

```text
.specify/sync/
```

## Agent choices

```bash
./hld_spec_sync.py --hld ./hld.md --agent devin
./hld_spec_sync.py --hld ./hld.md --agent claude
./hld_spec_sync.py --hld ./hld.md --agent codex
```

Default models by agent:

```text
devin  -> swe-1.6
claude -> opus-4.6
codex  -> gpt-5.5
custom -> no default model
```

Use `--model` to override the selected agent default:

```bash
./hld_spec_sync.py --hld ./hld.md --agent codex --model gpt-5.5
```

## Custom agent

```bash
./hld_spec_sync.py \
  --hld ./hld.md \
  --agent custom \
  --agent-command 'my-agent --prompt-file {prompt_file} --model {model}'
```

## Runner choice

Devin runs through a PTY-backed `pexpect` runner by default because some agent CLIs expect a terminal.

```bash
./hld_spec_sync.py --hld ./hld.md --agent devin --runner pexpect
./hld_spec_sync.py --hld ./hld.md --agent devin --runner subprocess
```

## Analyze only

```bash
./hld_spec_sync.py --hld ./hld.md --analyze-only
```

## Report only

```bash
./hld_spec_sync.py --hld ./hld.md --report-only
```

## Prompt only

```bash
./hld_spec_sync.py --hld ./hld.md --prompt-only
```

## HLD format report

For an existing large or raw HLD that is not yet in HLDspec format, generate a read-only conversion report:

```bash
./hld_spec_sync.py --hld HLD.md --hld-format-report
```

This does not call an agent, modify `HLD.md`, or write specs. It writes:

```text
logs/hld_spec_sync/<timestamp>/hld_format_report.md
logs/hld_spec_sync/<timestamp>/suggested_hld_sections.json
```

Use this before `--hld-map-only` when the HLD does not yet contain stable `## HLD-xxx - Title` sections.


## HLD map mode

Generate and validate an HLD section map without calling an agent:

```bash
./hld_spec_sync.py --hld HLD.md --hld-map-only
```

Map-aware sync can target one HLD section and build a bounded prompt from that section plus required references instead of loading the full HLD:

```bash
./hld_spec_sync.py --hld HLD.md --use-hld-map --target-hld HLD-003 --prompt-only
./hld_spec_sync.py --hld HLD.md --use-hld-map --target-hld HLD-003
./hld_spec_sync.py --hld HLD.md --use-hld-map --target-hld HLD-003 --resume
```

Generated map artifacts:

```text
.specify/sync/hld_ref_map.json
.specify/sync/hld_index.md
.specify/sync/hld_sections/<section-id>.md
```

Map-aware runs also write:

```text
logs/hld_spec_sync/<timestamp>/context_selection.json
.specify/sync/staged/<run-id>/proposed_writes.md
.specify/sync/staged/<run-id>/write_manifest.json
.specify/sync/chunks/run_state.json
```

The staged writes are created after WRITE FILE target validation and before final apply.
Use `--restart-map-run` to clear map-aware run state before rerunning a target.

### Resume support

`--resume` and `--restart-map-run` currently apply to `hld_spec_sync.py` map-aware target runs only.

Downstream map-aware runs do not yet support resume. Re-run downstream phases explicitly with `--target-hld` and/or `--target`.

Future downstream resume should include the phase, target HLD section, target specs, implementation roots, and input hashes in the run-state key.

## Skeptic mode

Use `--skeptic` to bake the Skeptic framework into the sync run. The agent must apply the flow from [`skeptic.md`](https://github.com/saffih/skeptic/blob/main/skeptic.md), close safe HLD/spec/constitution gaps, and write:

```text
.specify/sync/skeptic_report.md
.specify/sync/skeptic_conflicts.json
```

If unresolved conflicts remain, the script exits with code `2` after applying only allowed safe fixes. The JSON conflict file is the human-in-the-loop handoff.

```bash
./hld_spec_sync.py --hld ./hld.md --skeptic --agent codex
```

## Agent timeout

```bash
./hld_spec_sync.py --hld ./hld.md --agent-timeout-seconds 900
```

## Sync outputs

```text
.specify/memory/constitution.md
specs/<NNN-feature-slug>/spec.md
.specify/sync/spec_index.json
.specify/sync/feature_graph.json
.specify/sync/sync_report.md
.specify/sync/analyze_report.md
.specify/sync/missing_report.json
.specify/sync/duplicate_report.json
.specify/sync/drift_report.json
.specify/sync/constitution_change_report.md
logs/hld_spec_sync/<timestamp>/
```

## Downstream script

`hld_spec_downstream.py` continues after sync. It reads the HLD, constitution, native Spec Kit specs, and `.specify/sync/` reports, then drives downstream closure work:

- gap analysis
- gap closure plan
- Spec Kit planning artifacts
- task generation
- implementation closure report
- optional implementation file writes

Default downstream mode is planning-safe. It refuses implementation file writes unless `--allow-implementation` is set.
When implementation writes are allowed, at least one `--implementation-root` is required and protected paths such as `.git/`, `.agents/`, `.codex/`, `logs/`, and `.speckit*` remain forbidden.
Downstream writes are also phase-scoped: `analyze` writes downstream reports, `plan` writes planning artifacts, `tasks` writes `tasks.md`, and `implement` writes the closure report plus explicitly allowed implementation roots.

```bash
./hld_spec_downstream.py --hld ./hld.md --agent codex
```

Run only analysis:

```bash
./hld_spec_downstream.py --hld ./hld.md --phase analyze --agent codex
```

Target one or more specs:

```bash
./hld_spec_downstream.py --hld ./hld.md --target 006 --target 009 --agent codex
```

Allow implementation writes when you are ready to close code gaps:

```bash
./hld_spec_downstream.py \
  --hld ./hld.md \
  --phase implement \
  --allow-implementation \
  --implementation-root src \
  --agent codex
```

Set an agent timeout:

```bash
./hld_spec_downstream.py --hld ./hld.md --agent-timeout-seconds 900 --agent codex
```

Run downstream with Skeptic gap closure:

```bash
./hld_spec_downstream.py --hld ./hld.md --phase all --skeptic --agent codex
```

With implementation fixes:

```bash
./hld_spec_downstream.py \
  --hld ./hld.md \
  --phase implement \
  --skeptic \
  --allow-implementation \
  --implementation-root src \
  --agent codex
```

Downstream Skeptic mode writes:

```text
.specify/sync/downstream/skeptic_report.md
.specify/sync/downstream/skeptic_conflicts.json
```

If unresolved conflicts remain, downstream also exits with code `2` and leaves the conflict JSON as the human decision queue.

Prompt only:

```bash
./hld_spec_downstream.py --hld ./hld.md --prompt-only --agent codex
```

Map-aware downstream processing can target one HLD section and include only that section, required refs, normal refs within depth, mapped specs, and relevant downstream artifacts:

```bash
./hld_spec_downstream.py --hld HLD.md --hld-map-only
./hld_spec_downstream.py --hld HLD.md --use-hld-map --target-hld HLD-007 --phase plan --prompt-only
./hld_spec_downstream.py --hld HLD.md --use-hld-map --target-hld HLD-007 --phase plan
```

`--target-hld` and `--target` may be combined only when `--target` matches the section's `HLD-SPECS` mapping.

Map-aware downstream writes are staged and validated in a temporary workspace before they are applied to the real workspace.

### Resume support

`--resume` and `--restart-map-run` currently apply to `hld_spec_sync.py` map-aware target runs only.

Downstream map-aware runs should be rerun explicitly with `--target-hld`, `--target`, and `--phase`.

Future downstream resume must include phase, target HLD section, target specs, implementation roots, and input hashes.

## Downstream outputs

```text
.specify/sync/downstream/downstream_analysis.md
.specify/sync/downstream/gap_closure_plan.md
.specify/sync/downstream/implementation_closure_report.md
specs/<NNN-feature-slug>/plan.md
specs/<NNN-feature-slug>/research.md
specs/<NNN-feature-slug>/data-model.md
specs/<NNN-feature-slug>/quickstart.md
specs/<NNN-feature-slug>/contracts/
specs/<NNN-feature-slug>/tasks.md
logs/hld_spec_downstream/<timestamp>/
```

## Tests

```bash
PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 -m unittest discover -s tests -v
```
