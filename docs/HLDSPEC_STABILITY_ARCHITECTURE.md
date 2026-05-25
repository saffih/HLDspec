# HLDspec Stability Architecture

## Purpose

This document extends the current V2 direction. It does not replace
[`CANONICAL_FLOW.md`](CANONICAL_FLOW.md),
[`ARCHITECTURE_V2.md`](ARCHITECTURE_V2.md), or
[`HLDSPEC_STATE_MACHINE_CONTRACT.md`](HLDSPEC_STATE_MACHINE_CONTRACT.md).

**Goal:** Make HLDspec less brittle by separating core decisions from adapters,
treating artifacts as contracts, and making workflow transitions explicit and
testable.

---

## Core model

```
State + Message -> New State + Commands
```

| Concept | Meaning in HLDspec |
|---|---|
| **State** | Current workspace, checkpoint, gate, and artifact situation |
| **Message** | Something that happened (script ran, human replied, artifact written) |
| **Command** | Something the system should do next (run script, present checkpoint, block) |
| **Event** | Immutable fact that already happened (logged, not re-evaluated) |

This model is already implicit in the V2 machines. This document names it
explicitly so future slices extend it rather than working around it.

---

## Five principles

### 1. State machine core

HLDspec decisions must happen in the core state machine, not inside shell
scripts.

Shell scripts generate artifacts. Machines gate on artifact content. A script
that makes a workflow control decision (continue / block / branch) is a
hidden state machine — move that decision into the appropriate machine.

*Known failure mode this prevents:* shell scripts becoming hidden product logic.

### 2. Artifact contracts

Every generated artifact is an API. It must define:

```
schema_version
producer
consumers
required_fields
input_hashes
freshness_rules
validator
```

If a consumer cannot validate the artifact it is about to read, it is accepting
unverified input. Stale, partial, or schema-drifted artifacts pass gates silently.

*Known failure modes this prevents:* stale artifacts passing gates; queue and
dependency graph drift.

### 3. Ports and adapters

External systems should be behind replaceable interfaces:

```
SpecKitPort
ArtifactStorePort
HumanDecisionPort
AgentExecutionPort
GitPort
```

The SpecKit proxy subagent is already a partial implementation of `SpecKitPort`.
Naming the pattern makes the boundary testable and replaceable without touching
machine logic.

*Known failure modes this prevents:* one change breaking unrelated workflow
stages; legacy scripts controlling current flow.

### 4. Event log

Important transitions should eventually be recorded as immutable events:

```
previous_state
message
new_state
artifacts_read
artifacts_written
decision_owner
result
```

Without an event log, workflow history exists only in git commits and markdown
reports. Markdown reports must not become the controlling state.

*Known failure modes this prevents:* markdown reports becoming accidental
control state; agents editing state without evidence.

### 5. Validator plugins

Quality checks should be pluggable. Adding a new validator should not require
editing the main orchestrator.

`hldspec/prework_contracts.py` already implements several validators. The
pattern is correct; it just needs a stable registration seam so new checks
can be added without touching the orchestration path.

*Known failure modes this prevents:* SpecKit phase advancing without required
outputs; one change breaking unrelated stages.

---

## Known failure modes this prevents

| Failure mode | How a stability principle addresses it |
|---|---|
| Shell scripts becoming hidden product logic | Principle 1: decisions belong in machines |
| Stale artifacts passing gates | Principle 2: artifacts declare freshness rules |
| Queue and dependency graph drift | Principle 2: both artifacts share the same contract |
| Markdown reports becoming accidental control state | Principle 4: events are immutable; reports are rendering |
| Agents editing state without evidence | Principle 4: event log requires decision_owner + result |
| SpecKit phase advancing without required outputs | Principle 5: pluggable validators block advancement |
| Legacy scripts controlling current flow | Principle 3: adapters isolate legacy from core machines |
| One change breaking unrelated workflow stages | Principle 3: port boundaries contain blast radius |

---

## Non-goals

- This does not require a rewrite.
- This does not remove legacy scripts immediately.
- This does not implement a message bus yet.
- This does not replace SpecKit.
- This does not add process unless it prevents a known failure mode.

---

## Next small implementation slices

These are documentation anchors for future slices. None is required before
the next feature.

1. **Artifact contract registry skeleton** — `hldspec/artifact_contracts.py`:
   dataclass per artifact type; validate_contract() helper; tests.
2. **Artifact freshness validator** — extend `stale_prework_artifacts()` in
   `hldspec/prework_contracts.py` to cover all controlled artifacts, not just
   prework.
3. **Typed prework approval decision artifact** — replace ad-hoc dict with a
   validated schema; add schema_version and required fields.
4. **tests_v2 discovery in ready gate** — `hldspec_ready_gate.py` should
   confirm `tests_v2/` passes before reporting gate green.
5. **Shell-vs-ProjectMachine parity test** — assert that no shell script writes
   a gate decision that is not also validated by a machine.
6. **Replace deprecated "target-spec generation" active gate marker** — remove
   or archive the last uses of this phrase as a current next-step in active docs.

---

## Acceptance checklist

This document is accepted when:

- [x] It is concise — each section fits on one screen.
- [x] Every concept maps to a known HLDspec failure mode.
- [x] No broad runtime rewrite is required.
- [x] The V2 state-machine direction is explicitly supported.
- [x] Next slices are small and independently deliverable.
- [x] Referenced from `docs/DOCS_INDEX.md`.
- [x] `TASKS.md` updated with the architecture anchor entry.
