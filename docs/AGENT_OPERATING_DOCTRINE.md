# HLDspec Agent Operating Doctrine

**Status:** docs contract / agent-work doctrine.

This doctrine governs agents working on the HLDspec repo. It does not change
HLDspec runtime behavior, Journey behavior, helper behavior, target repo
behavior, SpecKit execution, or Constitution approval.

## 1. Purpose

Improve agent work quality on HLDspec by making repo-development behavior
repeatable: dispatch first, preserve context, use compact evidence, root-cause
failures, respect typed artifacts, and report decisions honestly.

## 2. Fixed baseline prompt

The fixed baseline prompt is this reusable operating doctrine.

Task-specific prompts define the concrete scope, files, checks, and desired
output for one slice.

The ponytail is a short non-negotiable reminder at the end of long prompts.

Rules:

- Use this doctrine as the baseline for HLDspec repo work.
- Task prompts may add scope and checks, but must not override doctrine
  boundaries.
- Improve or version this doctrine only after evidence from failures or repeated
  friction.

## 3. HLDspec minimality ladder

Before adding complexity, stop at the first rung that holds:

1. Does this need to be done in this gated slice?
2. Does an existing HLDspec doc/artifact/model already express it?
3. Is there one canonical source of truth to reuse?
4. Can an existing typed model / enum / bounded state represent it?
5. Can this remain docs-only for now?
6. Can it be one bounded slice with one verification path?
7. Only then add the minimum implementation.

Smallest safe change wins, but never by cutting evidence, tests, typed state,
human-owned decisions, RunSkeptic, security, data integrity, source-of-truth
checks, or approval gates.

## 4. Dispatch-first execution

The lead agent owns scope, architecture, risk, final synthesis, PR readiness,
and merge recommendation.

Workers or isolated micro-passes inspect bounded files, logs, tests, and diffs,
then return compact receipts.

The lead must not ingest broad raw repo context directly when a bounded receipt
can answer. If no true subagents are available, use isolated micro-passes and
explicitly report degraded context protection.

## 5. Context headroom

Preserve enough context for reasoning, failures, retries, and final synthesis.

Avoid full logs, full files, full diffs, and broad scans. Prefer compact
receipts: file/path, line range, fact, evidence, risk, recommendation.

When context gets tight, compact evidence before continuing. Stop broad
ingestion when bounded evidence is enough.

The context threshold is qualitative until measured; do not invent a numeric
token threshold yet.

## 6. Worker / micro-pass receipts

Receipt fields:

```text
TASK:
SCOPE:
FILES_OR_COMMANDS_INSPECTED:
EVIDENCE:
INFERENCE:
RISKS:
RECOMMENDATION:
UNCERTAINTY:
```

Rules:

- No full dumps unless exact evidence is required.
- Receipts do not decide architecture unless delegated.
- Receipts must distinguish evidence from inference.

## 7. Failure and retry doctrine

A failed run is untrusted until root-caused.

Do not surrender after first failure. Do not blindly rerun. Retry only after a
concrete hypothesis, input change, environment fix, or narrower repro.

Record the learning in the final report or follow-up prompt. Escalate to human
review when the failure remains unexplained, repeats after a reasoned retry, or
crosses product, security, or authority boundaries.

## 8. Evidence-based final report

Final report shape:

```text
EVIDENCE:
INFERENCE:
DECISION:
RISKS:
CHECKS_RUN:
UNCERTAINTY:
NEXT_ACTION:
```

Rules:

- Do not claim success without evidence.
- Cite tests, checks, lines, commits, or PRs when available.
- State uncertainty explicitly.
- Report what was not checked.

## 9. Single source of truth and typed artifacts

Every major HLDspec artifact should have one canonical source of truth. When an
artifact is machine-used, prefer one strong typed model with bounded states.

Agents and architecture tools must not invent parallel shapes when a canonical
model exists. Advisory outputs may reference canonical sources, but must not
duplicate them as independent truth.

Current HLDspec direction:

- Journey handoffs are typed.
- Journey 2 target package is authoritative for Journey 3.
- Helper capability facts derive from the helper registry.
- Journey 0 artifacts now have typed models.

## 10. Ponytail

Non-negotiables: dispatch first; compact receipts; preserve context headroom;
root-cause failures before retry; no blind reruns; reuse canonical docs/models;
smallest safe change wins; final report separates evidence, inference,
decision, risks, and next action.

The ponytail is a reminder, not a replacement for the doctrine. Do not turn the
ponytail into prompt bloat.

## 11. Constitution proposal boundary

This doctrine may inform future architecture/tooling rules. If a rule affects
generated target work, it may flow into Journey 2 as proposed constitution
material only. It must not bypass the Constitution approval gate or directly
modify the applied constitution.

## 12. Non-goals

This doc does not:

- implement runtime behavior,
- add validators,
- change Journey 0/1/2/3 behavior,
- change helper behavior,
- change target repo behavior,
- alter SpecKit execution,
- modify Constitution,
- replace RunSkeptic,
- require a specific external plugin such as Ponytail.
