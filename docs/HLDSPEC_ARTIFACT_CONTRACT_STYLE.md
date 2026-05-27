# HLDspec Artifact Contract Style

This document defines the standard shape for HLDspec handoffs, prompts, reports,
and policy files.

The goal is not to copy any external product. The goal is to make every HLDspec
artifact behave like a small interface contract: clear inputs, clear authority,
clear allowed actions, clear outputs, clear validation, and clear stop rules.

## Core rule

Every operational HLDspec artifact should state the following fields when they
are relevant:

```text
Purpose
Inputs
Authority
Allowed sources
Allowed actions
Forbidden actions
Expected outputs
Validation required
Stop conditions
Report format
Next owner
Evidence
```

If an artifact cannot say these things, it is probably not ready to be handed to
another agent.

## Why this exists

HLDspec coordinates human intent, HLD source truth, SpecKit phases, agents,
reviewers, and implementation slices. Without a stable artifact shape, work
becomes ambiguous: agents read the wrong files, skip gates, expand scope, or
implement without proof.

The contract style makes handoffs mechanically checkable and easier to resume.

## Required field meanings

### Purpose

What this artifact is for. One or two sentences.

### Inputs

The files, commands, source anchors, or decisions that must exist before the
artifact can be used.

### Authority

What this artifact may decide and what it may not decide.

Examples:

```text
HLD.md is product source truth.
.hldspec/source_package/ is HLDspec control truth.
.specify/source/ is generated read-only context.
.specify/ and specs/ are SpecKit-owned.
```

### Allowed sources

Files or evidence the receiving agent may read.

### Allowed actions

Actions the receiving agent may perform.

### Forbidden actions

Actions the receiving agent must not perform. This section should be explicit,
especially for implementation, source-truth changes, web use, broad scans,
legacy cleanup, and push/release actions.

### Expected outputs

The files, reports, commands, or classifications the artifact must produce.

### Validation required

The exact focused checks, regression checks, full test command, generated-output
smoke, and diff checks required before the work can be considered complete.

### Stop conditions

Conditions that force the agent to stop and return a report instead of
continuing.

Examples:

```text
missing required source
uncited product behavior
scope expansion
forbidden file touched
tests failed
human-owned decision required
RunSkeptic ACTION or CONFLICT
```

### Report format

The exact fields the agent must return after the phase.

### Next owner

Who owns the next decision: human, HLDspec judge, SpecKit proxy, consultant, or
implementation runner.

### Evidence

What proves the artifact was followed: command output, file paths, test results,
source anchors, phase reports, or coverage ledgers.

## Artifacts that must use this style

The following artifacts must either use this field shape directly or link to a
more specific template that does:

```text
SpecKit Run Card
Slice Execution Policy
Slice Implementation Prompt
Phase Report
Context Receipt
Gap Handoff
Consultant Review
RunSkeptic Report
Implementation Approval Packet
Release or Push Gate Packet
```

## Slice card shape

Every implementation slice should be expressible as a card:

```text
Slice
Purpose
Inputs
Authority
Allowed work
Forbidden work
Expected outputs
Focused tests
Regression tests
Stop conditions
Report format
Next owner
Evidence
```

Example:

```text
Slice: API
Purpose: expose approved use cases over HTTP or RPC.
Inputs: full SpecKit task graph, selected API task IDs, HLD anchors.
Authority: may add routes/controllers/mappers; may not invent business rules.
Allowed work: routes, request validation, response mapping, API tests.
Forbidden work: UI, new domain rules, unrelated persistence changes.
Expected outputs: API files, API tests, phase_report.json, anchor_coverage.json.
Focused tests: route, status code, error mapping, auth tests where relevant.
Regression tests: domain, contracts, persistence if API uses real storage.
Stop conditions: missing anchor, unapproved rule, failed tests, scope expansion.
Next owner: HLDspec judge for reassessment.
Evidence: commands run, test output, changed files, anchors covered.
```

## Gap handoff shape

A gap handoff is a status artifact, not architecture truth. It should use the
contract shape to make continuation safe:

```text
Current state
Known gaps
Dirty files
What changed
What was tested
What was not tested
Next safe patch
Forbidden actions
Validation required
Handoff prompt
```

## Relationship to README and canonical docs

- `README.md` is the conceptual front door.
- `docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md` is the canonical architecture and
  terminology source.
- `docs/SPECKIT_PROXY_PROTOCOL.md` defines how HLDspec instructs SpecKit.
- `docs/SPECKIT_SLICE_CONTROL.md` defines the slice-controlled implementation
  model.
- This document defines the reusable artifact/interface shape used by those
  workflows.

## Quality rule

An artifact is incomplete if it cannot answer:

```text
What may be read?
What may be changed?
What is forbidden?
What proves success?
When must the agent stop?
Who owns the next decision?
```
