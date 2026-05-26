# HLDspec Self-Dogfood Contract

## Purpose

HLDspec must be able to run on HLDspec itself.

The project should not only document source-of-truth, bounded context, quality gates, RunSkeptic, and promotion rules. It must prove those rules on its own development workflow.

## Contract

A user or weak/medium agent must be able to run the public HLDspec facade against HLDspec repository evidence and understand:

- current target state
- blockers
- evidence and reports
- human decisions required
- next safe action

without reading raw JSON first.

## Canonical self-dogfood source

The stable self-dogfood smoke source is:

```text
docs/HLDSPEC_DEVELOPMENT_BACKLOG.md
```

This file is used because it is durable HLDspec development evidence and contains active P0/P1/P2 work.

## Target workspace expectations

The self-dogfood target is a temporary target workspace in tests and may be a real target workspace in manual runs.

Required target artifacts after the smoke flow:

```text
target/.hldspec/agent_session.json
target/.hldspec/interview_answers.json
target/.hldspec/interview_answers.md
target/.hldspec/allowed_evidence.json
target/.hldspec/forbidden_reads.md
target/.hldspec/context_packs/<package-id>/context_pack.json
target/.hldspec/validation/context_prompt_validation.json
target/.hldspec/validation/context_prompt_validation.md
target/.hldspec/validation/promotion_gate.json
target/.hldspec/validation/promotion_gate.md
target/prompts/speckit/<package-id>/*.md
```

## Required commands

The self-dogfood smoke path must exercise:

```bash
scripts/hldspec start --source docs/HLDSPEC_DEVELOPMENT_BACKLOG.md --target <target>
scripts/hldspec status --target <target>
scripts/hldspec review --target <target>
scripts/hldspec doctor --target <target>
scripts/build_speckit_context_prompts.py <target>
scripts/validate_hldspec_target.py <target>
scripts/check_hldspec_promotion_gate.py <target>
```

The smoke path must not invoke SpecKit.

## PASS, ACTION, CONFLICT handling

- `PASS`: no blocking finding is known.
- `ACTION`: fixable missing, stale, invalid, or incomplete artifact.
- `CONFLICT`: unresolved design, source-of-truth, or human-owned decision.

A self-dogfood PASS does not mean HLDspec is product-complete. It means the current self-dogfood slice can run and report its state.

## Next-safe-action requirement

Every self-dogfood user-facing command must expose the next safe action.

At minimum:

- `status` includes `## Next Safe Action`
- `review` includes `## Next Safe Action`
- `doctor` includes `## Final Summary`

## Promotion implications

Capabilities that affect user workflow, prompt delegation, validators, gates, or target readiness should not be promoted beyond experimental status unless the self-dogfood smoke test still passes.

The promotion gate should eventually read self-dogfood evidence directly. Until then, `tests_v2/test_self_dogfood_flow.py` is the executable guard.
