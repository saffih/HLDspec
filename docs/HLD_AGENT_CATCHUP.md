# HLDspec Default Invocation

made by AI

Every project-level HLDspec invocation uses the judge/orchestrator role by default.

## Minimal user prompt

```text
HLDspec ./Flow-System-HLD.md
```

Replace `./Flow-System-HLD.md` with the project HLD path.

## Default agent contract

When the user invokes HLDspec on an HLD, the external coding agent must act as the HLDspec judge/orchestrator.

The agent runs:

```bash
~/code/HLDspec/scripts/hldspec_run.sh <path-to-HLD.md>
```

The agent continues only to the next safe checkpoint.

## Always true

- Do not modify the source HLD.
- Work inside `.hldspec-first-run` unless the human explicitly approves another path.
- Ask the human only at generated HLDspec human checkpoints.
- Do not answer human checkpoint questions yourself.
- Do not create specs, tasks, downstream analysis, or implementation unless the HLDspec gate allows it and the human approves the write step.
- Report briefly: what was run, what happened, checkpoint reached, and what decision is needed if any.

## If uv cache is sandbox-blocked

Use project-local cache:

```bash
UV_CACHE_DIR="$PWD/.hldspec-uv-cache" ~/code/HLDspec/scripts/hldspec_run.sh <path-to-HLD.md>
```
