# hld_spec_sync.py

Sync one large HLD into constitution, specs, index, graph, and reports.

## Install

```bash
chmod +x hld_spec_sync.py
```

## Default Devin run

```bash
./hld_spec_sync.py --hld ./hld.md --agent devin --model swe-1.6
```

## Greenfield

```bash
./hld_spec_sync.py --hld ./hld.md --mode greenfield
```

Greenfield compares the HLD desired state against an empty current state.

## Brownfield

```bash
./hld_spec_sync.py --hld ./hld.md --mode brownfield
```

Brownfield compares the HLD desired state against existing constitution/specs/index/graph.

## Auto mode

```bash
./hld_spec_sync.py --hld ./hld.md
```

Auto mode uses brownfield if specs/*/spec.md exists, otherwise greenfield.

## Agent choices

```bash
./hld_spec_sync.py --hld ./hld.md --agent devin  --model swe-1.6
./hld_spec_sync.py --hld ./hld.md --agent claude --model sonnet
./hld_spec_sync.py --hld ./hld.md --agent codex  --model gpt-5-codex
```

## Custom agent

```bash
./hld_spec_sync.py \
  --hld ./hld.md \
  --agent custom \
  --agent-command 'my-agent --prompt-file {prompt_file} --model {model}'
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

## Outputs

```text
.specify/memory/constitution.md
specs/spec_index.json
specs/feature_graph.json
specs/sync_report.md
specs/analyze_report.md
specs/missing_report.json
specs/duplicate_report.json
specs/drift_report.json
specs/constitution_change_report.md
specs/<NNN-feature-slug>/spec.md
logs/hld_spec_sync/<timestamp>/
```
