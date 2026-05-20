# HLD Spec Kit tools

Tools for turning one large HLD into native Spec Kit artifacts and continuing downstream toward implementation closure.

## Install

```bash
chmod +x hld_spec_sync.py
chmod +x hld_spec_downstream.py
```

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

Prompt only:

```bash
./hld_spec_downstream.py --hld ./hld.md --prompt-only --agent codex
```

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
