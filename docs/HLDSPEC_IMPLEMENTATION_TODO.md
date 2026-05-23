# HLDspec Implementation TODO

made by AI

Date: 2026-05-23

## Current milestone

Goal: make the first-run planning path safe enough to use as the product foundation before adding larger orchestration features.

## Done

- DONE: HLD section classifier marks stakeholder, persona, business case, executive summary, assumptions, and milestone sections as context-only.
- DONE: HLD section classifier marks decision log and open conflict sections as governance context.
- DONE: Explicit HLD-SPECS metadata still overrides context-only title classification.
- DONE: Buildable titles such as API/interface/data/system sections remain spec candidates.
- DONE: Focused classifier regression tests cover the false-positive first-feature cases.
- DONE: Plan-level regression test proves context-only sections do not become planned specs and do appear in context_hld_sections.
- DONE: Clean plan quality now reports PASS / KEEP_PLAN instead of FIX / KEEP_PLAN.
- DONE: RunSkeptic stabilization record captures the decision to fix the planner confidence gap before adding new product machinery.

## Next patch

- TODO: Add executable hld_usecase_api_map builder.
- TODO: Generate .specify/sync/hld_usecase_api_map.json.
- TODO: Generate .specify/sync/hld_usecase_api_map.md.
- TODO: Include actors, journeys, system use cases, API/interface surfaces, data/source-of-truth objects, feature candidates, context-only sections, dependencies, non-goals, risks, and open questions.
- TODO: Wire use-case/API map before prework package generation.
- TODO: Add prework gate that blocks SpecKit handoff when the first feature is context-only or not buildable.

## Later product wrappers

- TODO: Add hldspec_state.json and hldspec_state.md.
- TODO: Add scripts/hldspec_status.sh.
- TODO: Add scripts/hldspec_interview.sh.
- TODO: Add scripts/hldspec_prework.sh.
- TODO: Add scripts/hldspec_speckit_proxy.sh.
- TODO: Add bounded SpecKit proxy dossier generation.
- TODO: Add one-phase-at-a-time SpecKit proxy execution after explicit approval.

## Deferred decisions

- DEFERRED: Change unknown section default from SPEC_CANDIDATE to REVIEW_NEEDED. Reason: safer to preserve coverage until use-case/API map and prework gate exist.
- DEFERRED: Add full interview loop. Reason: requires hldspec_state and checkpoint queue ownership first.
- DEFERRED: Add SpecKit proxy. Reason: requires approved feature queue and bounded dossier first.

## Current readiness

- Classifier readiness: high.
- Planner gate readiness: medium-high after plan-level regression passes.
- Prework package readiness: medium.
- Product wrapper readiness: low.
- SpecKit proxy readiness: low.

## Rule

Do not add the next product layer until the current layer has a regression test and a clear stop condition.
