# HLDspec Product Scorecard

## Purpose

This scorecard measures whether HLDspec is becoming a simple, robust, agent-first product workflow.

## Current target state

| Area | Target |
|---|---|
| User workflow | Agent-first, one clear start command |
| Workspace | `target/` is the product workspace |
| HLD workspace | `target/targetHLD/` owns HLD evidence and working HLD |
| Architecture | Persistent command-event state machine |
| Scripts | Agent tools, not the user workflow |
| SpecKit | Owns final specs, plans, tasks, and implementation |
| RunSkeptic | Required at key junctions and when uncertain |
| Cost/context | Enforced in prompts and agent/tool selection |
| Backend choices | Short toolbox with default/upgrade triggers |
| Tests | Unit/integration/e2e expectations per package |

## Scorecard

| Capability | Desired score | Current risk |
|---|---:|---|
| Agent-first user model | 10 | Public docs may still lead with scripts |
| Simple start/resume UX | 10 | Needs CLI facade over machines |
| Target workspace clarity | 10 | Needs consistent implementation and docs |
| SpecKit ownership boundary | 10 | Strong; must preserve |
| State-machine architecture | 10 | Strong V2 direction; keep extending |
| Artifact freshness/diff | 10 | Needs more user-visible diff/status |
| Runtime use of guidance docs | 10 | Documented; needs machine enforcement |
| Backend technology recommendation | 10 | Documented; needs generated target artifact |
| RunSkeptic gates | 10 | Documented; needs more validator enforcement |
| Cost/context economy | 10 | Documented; needs prompt/tool enforcement |
| Testability per package | 10 | Must be validated in generated packages |
| CLI journey tests | 10 | Needed for product confidence |

## Highest priority improvements

1. Add public agent-first CLI facade.
2. Move user docs from scripts-first to agent-session-first.
3. Generate target-specific design principle selection.
4. Generate target-specific backend technology recommendation.
5. Validate package testability.
6. Validate prompt cost/context and RunSkeptic requirements.
7. Add CLI journey tests.
8. Keep low-level scripts as tools for agents.

## Definition of done

HLDspec is product-clean when this works:

```bash
hldspec start --source ./HLD.md --target ./target
hldspec status --target ./target
hldspec review --target ./target
hldspec continue --target ./target
```

And the user does not need to know internal script names unless debugging.
