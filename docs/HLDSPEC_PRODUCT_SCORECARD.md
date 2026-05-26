# HLDspec Product Scorecard

## Purpose

This scorecard measures whether HLDspec is becoming a simple, robust, agent-first product workflow.

It must not be used to promote HLDspec as product-ready unless blockers and evidence are current.

## Current target state

| Area | Target |
|---|---|
| User workflow | Agent-first, one clear start/resume/review path |
| Workspace | `target/` is the product workspace |
| HLD workspace | `target/targetHLD/` owns HLD evidence and working HLD |
| HLDspec state | `target/.hldspec/` owns HLDspec run state, sync artifacts, event log, validation, context packs, and promotion reports |
| SpecKit ownership | `target/.specify/` and `target/specs/` remain SpecKit-owned |
| Architecture | Persistent command-event state machine with explicit stops |
| Scripts | Agent/maintainer tools, not the user workflow |
| SpecKit delegation | Bounded prompts with allowed evidence, forbidden reads, model tier, stop condition, and RunSkeptic triggers |
| RunSkeptic | Required at key junctions, uncertainty points, and promoted capability claims |
| Cost/context | Enforced in prompts and agent/tool selection |
| Backend choices | Short toolbox with default/upgrade triggers |
| Tests | Unit/integration/e2e expectations per package plus product journey tests |

## Current readiness mark - 2026-05-26

Overall current mark: 6/10.

Product readiness: not product-ready. HLDspec has implemented foundations and gates, but guarded product-flow integration, end-to-end journey coverage, stale-artifact handling, domain validators, and RunSkeptic handoff propagation remain blockers.

Target mark before product-ready claim: 8/10 with passing journey tests, guarded product-flow gates, and RunSkeptic evidence propagation.

HLDspec is not fully product-ready.

| Area | Mark | Evidence | Remaining blocker |
|---|---:|---|---|
| Development handoff discipline | 7 | Handoff/backlog docs and generator exist. | Generated handoff needs stronger open-action, conflict, and RunSkeptic status quality. |
| Agent-first product model | 6 | Public commands are narrowed to `start`, `status`, `review`, `continue`, `diff`, and `doctor`; future and legacy/debug commands are classified. | Full end-to-end product journey coverage remains open. |
| Target workspace clarity | 7 | New-layout paths are stabilized for `.hldspec`, events, target HLD, raw HLD, and SpecKit-owned areas. | Remaining machines and docs need migration coverage. |
| TargetWorkspaceAdapter | 7 | `continue` calls ProjectMachine with new-layout metadata. | Not every machine path is proven through the adapter. |
| Use-case/API definition | 6 | Use-case catalog and command matrix exist. | Implementation and tests do not cover every use case. |
| Stateless external IO | 5 | `start` and self-dogfood smoke prove target-only durable writes for key flows. | Every write path is not yet enforced. |
| Context economy | 6 | Context packs, allowed evidence, forbidden reads, bounded prompts, and validators exist. | Not yet fully wired into guarded product flow. |
| SpecKit delegation prompts | 6 | Seven bounded phase prompts are generated per package. | Package discovery, invocation wiring, and output verification remain. |
| Validators and regression gates | 6 | Context validator, promotion gate, matrix tests, command/path tests, and self-dogfood smoke exist. | Domain validators remain open. |
| RunSkeptic enforcement | 6 | Prompt validation and promotion gate enforce RunSkeptic requirements; promoted capabilities require RunSkeptic PASS evidence. | Gate-machine and handoff outputs do not yet propagate RunSkeptic status. |
| Promotion gate | 6 | Gate blocks validator ACTION/CONFLICT, missing context validation, unresolved checkpoints, readiness >7 without evidence, and promoted capability claims without RunSkeptic PASS evidence. | No complete guarded product promotion path yet. |
| UX/output quality | 6 | `status`, `review`, and `doctor` expose blockers, validation status, promotion status, next safe action, and final summary. | `start`, `diff`, and stage-aware doctor checks need more coverage. |
| Self-dogfood | 6 | Self-dogfood smoke runs on HLDspec backlog evidence without invoking SpecKit. | Full self-hosted SpecKit delegation remains unproven. |

## Remaining blockers

HLDspec cannot be called product-ready until these are addressed:

1. Guarded product-flow integration: context validation, RunSkeptic gates, and promotion gate must run at the right product stops.
2. End-to-end journey tests: start, resume, review, continue, conflict stop, prompt generation, validation, promotion, status, and doctor must be covered through the facade.
3. Stale-artifact and diff handling: changed source/guidance/generated artifacts must be detected and reported.
4. Domain validators: backend triggers, principle evidence, constitution purity, package testability, dependency graph/queue parity, and handoff pointers must be validated.
5. RunSkeptic propagation: gate-machine, handoff, and review outputs must expose PASS/ACTION/CONFLICT status with evidence links.
6. Documentation alignment: README, AGENTS, CLAUDE, USER_RUN_MODEL, use cases, and command matrix must agree on current/future/legacy commands.

## Promotion rules

- Do not raise the overall mark above 7 without tests or reproduced evidence for each promoted capability.
- A promoted capability must include RunSkeptic PASS evidence.
- ACTION or CONFLICT findings from context validation or promotion gate block promotion.
- Readiness marks above 7 require explicit evidence in the scorecard or generated promotion report.
- A target readiness promotion requires `target/.hldspec/validation/promotion_gate.json` status `PASS`.

## Scorecard

| Capability | Desired score | Current score | Current risk |
|---|---:|---:|---|
| Agent-first user model | 10 | 6 | Facade exists, but full journey orchestration is incomplete. |
| Simple start/resume UX | 10 | 6 | `start` and `continue` exist; resume/adopt/update journeys need tests. |
| Target workspace clarity | 10 | 7 | Core path contract is clear; remaining migration coverage is incomplete. |
| SpecKit ownership boundary | 10 | 8 | Boundary is strong; generated prompts must preserve it. |
| State-machine architecture | 10 | 7 | ProjectMachine direction is strong; more transitions need product tests. |
| Artifact freshness/diff | 10 | 3 | Stale detection is still a blocker. |
| Runtime use of guidance docs | 10 | 5 | Guidance exists; machine enforcement is partial. |
| Backend technology recommendation | 10 | 4 | Documented; target-specific generated validation remains open. |
| RunSkeptic gates | 10 | 6 | Prompt and promotion checks exist; status propagation remains open. |
| Cost/context economy | 10 | 6 | Generated prompts and validators exist; guarded product-flow integration remains open. |
| Testability per package | 10 | 4 | Required in prompts; not yet semantically validated in generated packages. |
| CLI journey tests | 10 | 5 | Contract and smoke tests exist; complete journey coverage is missing. |
| UX/output quality | 10 | 6 | Status/review/doctor improved; all commands need the same output contract. |
| Self-dogfood | 10 | 6 | Smoke exists; full self-hosted delegation and stale rebuilds remain open. |
| Promotion evidence | 10 | 6 | Promotion gate requires promoted capability RunSkeptic evidence; generated scorecard evidence remains open. |

## Next safe step

Review GitHub diff and RunSkeptic on the backlog/scorecard truth update before further implementation.

After that, the next implementation step is guarded product-flow integration for context validation, RunSkeptic status, and promotion gating.

## Definition of done

HLDspec is product-clean when this works through the public facade without direct low-level script knowledge:

```bash
hldspec start --source ./HLD.md --target ./target
hldspec status --target ./target
hldspec review --target ./target
hldspec continue --target ./target
hldspec diff --target ./target
hldspec doctor --target ./target
```

Required product-clean evidence:

- source evidence remains unchanged
- target state is written only under approved target paths
- interview/session artifacts are written
- context economy artifacts are generated
- bounded SpecKit prompts are generated
- context validation report is PASS
- promotion gate report is PASS
- promoted capabilities include RunSkeptic PASS evidence
- unresolved human checkpoints stop continuation
- status/review/doctor show blockers and next safe action
