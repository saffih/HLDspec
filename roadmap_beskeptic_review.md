# HLDspec Roadmap RunSkeptic Self-Review

made by AI

## Purpose

This report audits the HLDspec roadmap and current solution before adding more implementation.

The goal is to ensure HLDspec can support this repeated process:

```text
Raw or existing HLD
-> HLD_FORMAT report
-> Canonical HLD
-> HLD Map
-> Spec Build Plan
-> Target Spec
-> Coverage Gate
-> Integration Gate
-> Downstream plan/tasks
-> Implementation
-> Repeat safely as the HLD changes
```

This is a self-review of our roadmap and solution, not a repo change.

## Method

Use the real Skeptic Framework:

```text
GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN
```

HLDspec term:

```text
RunSkeptic review = HLDspec operational use of the real Skeptic flow on selected Key Aspects.
```

Top-level decisions:

```text
FIX
DECOMPOSE
CONFLICT
```

Final outcomes:

```text
HANDLED
CONFLICT
```

## Evidence base

Current known repo state from GitHub main:

- `AGENTS.md` defines HLDspec operating rules vs target Spec Kit Constitution.
- `TERMINOLOGY.md` defines canonical terms.
- `README.md` explains target constitution distinction.
- `AGENTS.md` distinguishes current `--target-hld` workflow from intended bottom-up workflow.
- `hld_spec_sync.py` now implements read-only `--plan-specs`.
- `--plan-specs` generates `.specify/sync/spec_build_plan.json` and `.specify/sync/spec_build_plan.md`.
- `--plan-specs` calls no agent and writes no specs.
- Existing test coverage includes a helper-level Spec Build Plan test, but not yet a CLI-level `--plan-specs` test.

## Roadmap under review

Current roadmap:

```text
1. HLD operating rules and terminology
2. HLD format report
3. HLD map
4. Current bounded target-hld workflow
5. Read-only Spec Build Plan
6. Plan Quality Gate
7. Target Spec prompt-only
8. Target Spec generation
9. Coverage Gate
10. Integration Gate
11. Downstream target-spec flow
12. Implementation gating
13. Iterative repeat / drift handling
```

## Cycle 1: Is the roadmap solving the real problem?

### Key Aspects

- `scope_done`
- `source_of_truth`
- `testability`
- `user_decision`

### Skeptic Spotlight

Does the roadmap solve the real need: repeatably move from HLD to Spec Kit to quality modifiable software?

### Thinkers

- CH: What depends on this roadmap?
- OM: Is the roadmap more complex than needed?
- FE: Can a user follow it?
- PO: What would prove the roadmap wrong?
- KT: Should every project use this flow?
- SH: Is this a real integration or a bad compromise?

### Findings

The roadmap is solving the right problem. The issue was not only HLD size. The issue was:

- HLD sections are not specs.
- Spec boundaries must be capability-based.
- Specs must be built bottom-up.
- API contracts must be explicit.
- Coverage must be checked after each spec.
- Integration must be checked before downstream.
- The process must be repeatable as the HLD changes.

### Decision

```text
FIX
```

Roadmap direction is correct, but it needs stricter gates before moving to target-spec generation.

### Outcome

```text
HANDLED with required next fix: Plan Quality Gate
```

## Cycle 2: Is the roadmap minimal?

### Key Aspects

- `scope_done`
- `spec_decomposition`
- `bottom_up_order`
- `testability`

### Skeptic Spotlight

Are we adding too much process before proving usefulness?

### Thinkers

- CH: What parts depend on earlier parts?
- OM: Can anything be removed?
- FE: Is there a simpler safe path?
- PO: What would fail if we skip a step?
- KT: Should this be universal?
- SH: Is the middle path real integration?

### Findings

The roadmap should not implement all intended commands at once.

Correct decomposition:

```text
Current safe state:
Format Report + HLD Map + target-hld + read-only plan-specs

Next:
Plan Quality Gate

Not yet:
target-spec
coverage-check
integration-check
downstream target-spec execution
```

### Decision

```text
DECOMPOSE
```

### Outcome

```text
HANDLED
```

Do not move to `--target-spec` yet.

## Cycle 3: Is `--plan-specs` sufficient?

### Key Aspects

- `spec_boundary`
- `spec_decomposition`
- `api_contract`
- `coverage`
- `integration`
- `performance`
- `memory`
- `dependency_order`

### Skeptic Spotlight

Can the current read-only Spec Build Plan be trusted as the bridge from HLD sections to capability specs?

### Thinkers

- CH: What downstream steps depend on the plan?
- OM: Does it assume too much from `HLD-SPECS`?
- FE: Is its output explainable?
- PO: What would prove the plan wrong?
- KT: Should explicit `HLD-SPECS` always be trusted?
- SH: Is section mapping vs capability planning a real conflict?

### Findings

`--plan-specs` is the right first bridge, but it is currently too trusting.

Specific concern:

```text
If multiple HLD sections share the same explicit HLD-SPECS value,
the planner groups them without enough challenge.
```

This may be valid when those sections feed one capability. It is dangerous when they mix layers:

```text
governance + data + API + processing + operations
```

### Decision

```text
FIX
```

### Required fix

Add a top-level `plan_quality` object and per-spec quality flags.

Plan Quality Gate should detect:

- one planned spec contains multiple layers
- one planned spec mixes governance/data/API/processing/operations/testing
- one planned spec contains both API contract and processing behavior without explicit boundary
- explicit `HLD-SPECS` mappings look suspicious
- high-risk sections lack verification
- performance/memory concerns are relevant but missing expectations
- dependency order conflicts or cycles exist
- target constitution action is `conflict`

### Outcome

```text
CONFLICT until Plan Quality Gate exists
```

## Cycle 4: Should we implement `--target-spec` next?

### Key Aspects

- `spec_boundary`
- `coverage`
- `integration`
- `staged_write_safety`
- `reversibility`
- `testability`

### Skeptic Spotlight

Is it safe to create/update one Target Spec before the plan can criticize itself?

### Thinkers

- CH: What depends on target-spec output?
- OM: Can target-spec wait?
- FE: Would the user understand the risk?
- PO: What would prove target-spec is premature?
- KT: Should every plan go straight to spec generation?
- SH: Is speed vs correctness a real conflict?

### Findings

Not safe yet.

Without Plan Quality Gate, target-spec could faithfully generate the wrong spec boundary.

### Decision

```text
DECOMPOSE
```

### Outcome

```text
Do not implement target-spec next.
```

## Cycle 5: Coverage challenge

### Key Aspects

- `coverage`
- `hld_refs`
- `feature_graph`
- `source_of_truth`

### Skeptic Spotlight

What makes HLD coverage hard?

### Thinkers

- CH: What depends on coverage?
- OM: What is the minimum coverage proof?
- FE: Can coverage be read by humans?
- PO: What would prove coverage false?
- KT: Should every HLD anchor map to a spec?
- SH: Is strict coverage vs practical progress a real tradeoff?

### Findings

Coverage is hard because:

- one HLD section may feed multiple specs
- one spec may cover multiple HLD sections
- normal refs may matter but not be required dependencies
- HLD anchors may be stale after edits
- multiple specs may duplicate a capability
- source sections may be partially covered
- some HLD content belongs in the target Spec Kit Constitution, not a feature spec

### Decision

```text
DECOMPOSE
```

### Required future gate

Coverage Gate must classify:

```text
full
partial
uncovered
stale
duplicate
wrong_mapping
conflict
```

### Outcome

```text
Not next; implement after target-spec exists.
```

## Cycle 6: Integration/API challenge

### Key Aspects

- `integration`
- `api_contract`
- `producer_consumer`
- `dependency_order`
- `data_state_ownership`
- `performance`
- `memory`
- `reliability`
- `failure_recovery`

### Skeptic Spotlight

What makes integration/API correctness hard?

### Thinkers

- CH: Who depends on each contract?
- OM: Where can we simplify interface ownership?
- FE: Is the contract visible?
- PO: What fails silently if the contract is missing?
- KT: Should implicit contracts be allowed?
- SH: Is producer-owned vs shared-interface-owned contract a real conflict?

### Findings

Integration/API correctness is hard because specs can look complete independently but fail together.

Integration Gate must eventually prove:

- producer spec is named
- consumer specs are named
- API contract artifact or spec section exists
- data/state ownership is explicit
- dependency edge exists
- failure/retry/recovery behavior is specified
- performance/memory constraints are not hidden

### Decision

```text
DECOMPOSE
```

### Outcome

```text
Not next; make --plan-specs record integration expectations first.
```

## Cycle 7: Performance and memory

### Key Aspects

- `performance`
- `memory`
- `latency`
- `scalability`
- `bounded_context`

### Skeptic Spotlight

How should HLDspec handle performance/memory without creating noise?

### Thinkers

- CH: What breaks under load?
- OM: Where is resource analysis unnecessary?
- FE: Can "not applicable" be explicit?
- PO: What would falsify the assumptions?
- KT: Should all specs require performance criteria?
- SH: Is completeness vs noise a real conflict?

### Findings

Performance and memory must be first-class but selective.

Relevant when HLD/spec involves:

- large HLD or context size
- prompt budget
- model output size
- data volume
- API latency
- retry loops
- persistence
- event volume
- runtime implementation
- high-risk operational behavior

Not every governance or wording-only spec needs resource constraints.

### Decision

```text
FIX
```

### Required fix

Plan Quality Gate should flag:

```text
performance_or_memory_relevance_unknown
```

when terms suggest runtime/resource impact but no expectations exist.

## Cycle 8: Tests and verification

### Key Aspects

- `testability`
- `verification_path`
- `reversibility`

### Skeptic Spotlight

Does the current test set prove the behavior we need?

### Thinkers

- CH: Which downstream errors matter?
- OM: What tests are the minimum?
- FE: Are tests understandable?
- PO: What would prove the current tests insufficient?
- KT: Should every CLI command have a CLI test?
- SH: Is unit vs CLI coverage a real tradeoff?

### Findings

Current `--plan-specs` test checks the helper, not the CLI.

Needed now:

- CLI test for `--plan-specs`
- verify outputs exist
- verify no specs are created
- verify no agent is called
- verify run summary says `mode: plan-specs`

### Decision

```text
FIX
```

### Outcome

```text
Next patch should include CLI test.
```

## Cycle 9: Brownfield correctness

### Key Aspects

- `source_of_truth`
- `feature_graph`
- `coverage`
- `integration`
- `dependency_order`

### Skeptic Spotlight

Can the plan handle an existing Spec Kit workspace?

### Thinkers

- CH: What depends on brownfield accuracy?
- OM: Can brownfield wait?
- FE: Is current behavior honest?
- PO: What would prove brownfield unsafe?
- KT: Should plan-specs always compare existing specs?
- SH: Is greenfield vs brownfield a real conflict?

### Findings

Current `--plan-specs` mostly uses HLD map evidence. It does not deeply compare:

- existing specs
- spec_index
- feature_graph
- current target constitution

This is acceptable for first read-only plan if the output is honest, but not enough for full brownfield correctness.

### Decision

```text
DECOMPOSE
```

### Outcome

```text
Later feature: Brownfield Plan Reconciliation.
```

Do not add it before Plan Quality Gate.

## Stabilized roadmap decisions

| Roadmap item | Decision | Status |
|---|---|---|
| Operating rules / terminology | FIX | HANDLED |
| Format Report | FIX | HANDLED |
| HLD Map | FIX | HANDLED |
| target-hld workflow | FIX | HANDLED as current supported path |
| read-only plan-specs | FIX | HANDLED as first bridge |
| Plan Quality Gate | FIX | NEXT |
| target-spec | DECOMPOSE | NOT YET |
| Coverage Gate | DECOMPOSE | AFTER TARGET-SPEC |
| Integration Gate | DECOMPOSE | AFTER TARGET-SPEC |
| Downstream target-spec | DECOMPOSE | AFTER COVERAGE/INTEGRATION |
| Brownfield reconciliation | DECOMPOSE | LATER |
| Full implementation gating | DECOMPOSE | LATER |

## Next patch requirements

Next patch: **Plan Quality Gate for `--plan-specs`**.

It must remain read-only.

It must add:

```json
{
  "plan_quality": {
    "decision": "FIX|DECOMPOSE|CONFLICT",
    "recommendation": "KEEP_PLAN|REVIEW_PLAN|SPLIT_PLANNED_SPEC|RESOLVE_CONFLICT",
    "findings": [],
    "conflicts": [],
    "RunSkeptic_cycles": []
  }
}
```

It must add per planned spec:

```json
{
  "quality_flags": [],
  "layer_mix": [],
  "responsibility_mix": [],
  "boundary_risk": "low|medium|high",
  "requires_user_review": true
}
```

It must detect:

- mixed layers in one planned spec
- multiple HLD roles in one planned spec
- API + processing + data + operations mixed in one planned spec
- suspicious explicit `HLD-SPECS` groupings
- high-risk sections without verification
- performance/memory concerns without expectations
- conflict refs
- dependency ambiguity

It must add CLI-level test:

```bash
./hld_spec_sync.py --hld HLD.md --use-hld-map --plan-specs
```

Test assertions:

- `.specify/sync/spec_build_plan.json` exists
- `.specify/sync/spec_build_plan.md` exists
- no `specs/*/spec.md` is created
- no `.specify/memory/constitution.md` is created by `--plan-specs`
- run summary mode is `plan-specs`
- mixed responsibility spec is flagged

## What not to do next

Do not implement:

- `--target-spec`
- `--coverage-check`
- `--integration-check`
- auto-conversion
- auto-chunk execution
- multi-spec execution
- implementation generation

until Plan Quality Gate is implemented and tested.

## Final self-review decision

```text
Decision: FIX
Next action: Plan Quality Gate
Outcome: HANDLED if implemented and tested
```

