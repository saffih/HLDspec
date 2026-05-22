# Context Tailoring Protocol

made by AI

This protocol defines how HLDspec chooses the right agent, prompt, context, and cost level for each task.

Core rule:

```text
HLDspec should use the weakest sufficient agent, the smallest sufficient context, and the strictest sufficient prompt.
```

## Purpose

HLDspec must avoid context bloat and overpowered delegation.

The judge/orchestrator should not give every task to a high-reasoning agent with the full HLD, full repo, full conversation, and all historical decisions.

Instead, HLDspec must tailor the task context to the task.

## Context tailoring

Context tailoring means every task receives only:

```text
- the task goal
- the minimum relevant files or HLD sections
- prior decisions only when they affect this task
- applicable rules only
- required output schema
- forbidden actions
- stop condition
- escalation rule
```

The task should not receive:

```text
- full conversation history
- full HLD unless required
- full repo unless required
- unrelated prior decisions
- every HLDspec protocol
- implementation context outside the task
```

## Bloat guard

The judge/orchestrator must ask before delegation:

```text
What is the smallest sufficient context?
What is the weakest sufficient agent?
What is the strictest sufficient prompt?
Can this be done by grep, a script, or a deterministic check?
Can this be delegated to a smaller subagent?
What is the stop condition?
```

If a task can be completed by a deterministic check, script, grep, or exact-marker test, the judge must not spend high-reasoning budget on it.

## Cost-fit delegation

The judge/orchestrator must classify each task before delegation.

```text
Task type:
- MECHANICAL
- BOUNDED_ANALYSIS
- ARCHITECTURE_DECISION
- HUMAN_CHECKPOINT
- SPECKIT_PROXY
- BESKEPTIC_REVIEW

Required capability:
- level_0_deterministic
- level_1_weak_simple_agent
- level_2_medium_bounded_agent
- level_3_strong_reasoning_agent
- level_4_extra_high_reasoning_agent
```

Use the lowest level that can reliably complete the task.

## Agent strength ladder

### Level 0 - deterministic tool/script

Use for:

```text
grep
find
sed -n
exact marker checks
metadata validation
format validation
file existence checks
unit test execution
```

Prompt style:

```text
Run exactly this check.
Return FOUND or MISSING.
Do not infer.
Do not edit.
Stop after the result.
```

### Level 1 - weak/simple agent

Use for:

```text
mechanical patching
small markdown cleanup
small test failure repair
copying exact wording
extracting listed facts
```

Prompt style:

```text
Use only the listed file.
Make only the requested edit.
Do not expand scope.
Do not infer architecture.
Run the specified test.
Stop.
```

### Level 2 - medium bounded agent

Use for:

```text
section classification
small local refactor
conversion index generation
bounded report generation
ordinary test failure diagnosis
```

Prompt style:

```text
Use only these artifacts.
Classify or patch only this bounded scope.
Return structured evidence and confidence.
Escalate if architecture or human-owned decisions appear.
```

### Level 3 - strong reasoning agent

Use for:

```text
constitution rule review
dependency graph review
API contract vs processing split
checkpoint state conflicts
cross-artifact contradiction resolution
```

Prompt style:

```text
Use bounded architecture context.
Present evidence.
Show tradeoffs.
Return PASS / ACTION / CONFLICT.
Do not implement.
Do not invoke SpecKit.
Escalate human-owned decisions.
```

### Level 4 - extra-high reasoning agent

Use only for:

```text
repeated contradictions
canonical flow redesign
deep Beskeptic meta-review
HLDspec vs SpecKit ownership boundary conflicts
large process failures that lower levels could not resolve
```

Prompt style:

```text
Resolve one major process or architecture conflict.
Do not add new concepts unless required.
Prefer simplification.
Produce one small patch or no patch.
```

## Strict prompt rule

The simpler the task, the stricter the prompt.

```text
Simple task:
- exact files
- exact command/check
- exact output
- no interpretation
- no expansion
- stop after result

Complex task:
- bounded reasoning
- explicit tradeoffs
- evidence
- escalation rule
- affected artifacts
- stop condition
```

## Nested delegation

Subagents may delegate to smaller subagents only when delegation reduces cost or risk.

A subagent may delegate only if:

```text
1. the delegated task is narrower than the parent task
2. the delegated agent receives less context
3. the delegated prompt is stricter
4. the delegated agent has less authority
5. the delegated agent cannot make human-owned decisions
6. the parent verifies the result before using it
```

Every delegation must reduce at least one of:

```text
- context size
- reasoning complexity
- cost
- authority
- blast radius
```

## Authority boundary

Delegated agents may collect evidence, classify, validate, and recommend.

Only the judge/orchestrator may:

```text
- decide checkpoint state
- ask the human
- record human decisions
- approve continuation
- authorize SpecKit invocation
- authorize implementation
```

## Required context package

Every delegated task must have a task context package.

```text
Task:
Agent level:
Agent personality:
Allowed context:
Forbidden context:
Allowed tools:
Forbidden actions:
Required output:
Stop condition:
Escalation rule:
```

## HLDspec task mapping

| Task | Default level | Notes |
|---|---:|---|
| grep/find/exact marker check | 0 | deterministic |
| metadata validation | 0 | script preferred |
| markdown wording cleanup | 1 | exact patch only |
| small test failure repair | 1-2 | escalate if architecture appears |
| raw HLD conversion | 2 | preservation-first |
| HLD section classification | 2 | bounded analysis |
| API-vs-processing split review | 3 | architecture-sensitive |
| constitution rule review | 3 | evidence required |
| dependency graph review | 3 | architecture-sensitive |
| Beskeptic meta-review | 3-4 | use 4 only for major conflicts |
| SpecKit proxy run | 2-3 | one feature at a time |
| implementation approval | judge only | human-owned gate |

## Review checklist

Before a judge/orchestrator delegates, it must verify:

```text
- Is this task narrower than the parent goal?
- Is the context package minimal?
- Is the prompt strict enough for the task simplicity?
- Is the chosen agent the weakest sufficient one?
- Are human-owned decisions protected?
- Is the stop condition explicit?
- Will the parent verify the result?
```

## Failure modes

Context tailoring fails when:

```text
- a low-cost task is given to a high-reasoning agent
- a subagent receives the full HLD when only one section is needed
- a subagent receives all protocols when one rule applies
- a subagent can decide a human-owned question
- a parent accepts delegated output without verification
- prompts become broad because the task is simple
```

## Summary

```text
HLDspec should not maximize intelligence per task.
HLDspec should maximize fit:
- weakest sufficient agent
- smallest sufficient context
- strictest sufficient prompt
- lowest sufficient cost
```
