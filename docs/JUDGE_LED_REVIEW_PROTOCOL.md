# Judge-Led Review Protocol

This protocol defines how HLDspec turns review questions into explicit human decisions without letting agents silently promote artifacts.

## Purpose

The judge owns artifact promotion. Review agents, product agents, architecture agents, and SpecKit proxy agents may propose evidence-backed changes, but they do not approve product scope, architecture boundaries, source-of-truth ownership, dependency order, split/merge choices, constitution changes, or implementation start.

## Feedback Impact Map

Every human answer must be mapped before the next artifact is promoted.

Required fields:

```text
question_id
answer
Human Decision Owner
Affected Artifact
decision_type
evidence_sources
rebuild_required
next_safe_action
```

## Affected Artifact

An Affected Artifact is any generated or controlling file whose meaning changes because of a human answer.

Common examples:

```text
HLD.md workspace copy
hld_decision_log.json
spec_build_plan.json
speckit_input_manifest.json
speckit_invocation_queue.json
constitution_update_plan.json
feature_dependency_graph.json
speckit_prework_quality_review.json
speckit_proxy_dossier.json
hldspec_speckit_spec_list.json
hldspec_architecture_findings_disposition.json
hldspec_speckit_readiness.json
```

## Rebuild Loop

When a human answer changes an Affected Artifact, the judge must rebuild downstream artifacts in dependency order.

```text
record answer
update decision log
rebuild affected artifact
rebuild downstream reviews
rerun RunSkeptic when the step is critical
show the changed review surface
ask for approval only when blockers are gone
```

Do not reuse stale readiness, quality, or promotion artifacts after an answer changes their inputs.

## What I Will Do After You Answer

Marker phrase for generated checks: What I will do after you answer.

For every checkpoint question, the judge must tell the human what will happen after the answer is recorded.

The answer must name:

```text
files that will be updated
reviews that will be rerun
whether SpecKit remains forbidden
whether implementation remains forbidden
the next checkpoint
```

## Promotion Rule

Promotion requires the judge to verify:

```text
no blocking RunSkeptic finding remains
no review-required status remains unresolved
all human-owned decisions have a Human Decision Owner answer
all Affected Artifacts were rebuilt
tests or deterministic checks passed
```

If any condition is false, the result is still proposed, not approved.
