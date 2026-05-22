# HLDspec Ready Gate

made by AI

This gate decides whether HLDspec is ready for paid agent/SpecKit testing.

## Rule

Do not spend paid agent/SpecKit credits until the local no-credit readiness gate reports:

```text
READY_FOR_PAID_AGENT_TEST
```

## Command

```bash
uv run python scripts/hldspec_ready_gate.py \
  --repo . \
  --output-dir .hldspec-ready-gate \
  --fail-on-not-ready
```

Optional Flow dry checkpoint, still local/no-agent:

```bash
uv run python scripts/hldspec_ready_gate.py \
  --repo . \
  --output-dir .hldspec-ready-gate \
  --flow-hld ~/code/flow/Flow-System-HLD.md \
  --fail-on-not-ready
```

## What the gate checks

- required HLDspec files exist
- RunSkeptic naming/file tests pass
- raw-HLD marking test passes
- product-readiness plan-quality fixtures pass
- SpecKit prework/proxy tests pass
- full unittest discovery passes
- optional Flow checkpoint stops safely
- no paid agent, SpecKit, implementation, or final spec generation is invoked

## Output

```text
.hldspec-ready-gate/hldspec_ready_gate.json
.hldspec-ready-gate/hldspec_ready_gate.md
```

## Interpretation

`READY_FOR_PAID_AGENT_TEST` means HLDspec is ready for the next bounded paid-agent test.

`NOT_READY` means fix the listed blockers before spending credits.

## Agent command integration

The readiness gate is phase 0 of the full agent command:

```text
HLDspec <path-to-HLD>
```

The agent must run this gate before spending paid agent/SpecKit credits.

If the gate is NOT_READY, stop and fix HLDspec first.

If the gate is READY_FOR_PAID_AGENT_TEST, continue to one bounded target-HLD checkpoint run.

## Flow checkpoint exit code

`rc=2 is accepted when checkpoint artifacts exist`.

This means the Flow dry run reached a safe HLDspec checkpoint that requires human review, such as raw-HLD conversion decisions or SpecKit prework approval. It is not treated as a readiness failure when the expected checkpoint artifacts were written.
