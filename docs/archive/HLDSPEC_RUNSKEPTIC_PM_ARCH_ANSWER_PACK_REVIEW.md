# HLDspec Product/Architect Answer Pack RunSkeptic Review

Date: 2026-05-23

## Source of truth

RunSkeptic source read before this patch:

- Repository: `saffih/skeptic`
- File: `skeptic.md`
- Required flow: `GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN`

## Goal

Before any real SpecKit execution, create explicit Product Manager and Architect role outputs, then build a SpecKit answer pack from them.

## GATE

DONE is testable:

- Product Manager pack creates use cases, user stories, acceptance criteria, and product open questions.
- Architect pack creates architecture boundaries and architecture open questions.
- Answer pack combines both role outputs.
- Proxy dry-run refuses readiness when answer pack is missing or has blocking open questions.
- Tests cover open questions and user story extraction.

Wrong-answer cost is bounded:

- only derived workspace artifacts are written
- source HLD is not modified
- real SpecKit is not invoked
- implementation remains blocked

Decision: FIX allowed.

## FUNDAMENTAL SCAN

Source of truth:

- `hld_usecase_api_map.json` is the source for user stories/use cases/open questions.
- Product Manager owns product questions and acceptance criteria.
- Architect owns API/data/dependency/constitution questions.
- `speckit_answer_pack.json` is the proxy input gate.

Boundary:

- Product Manager pack does not decide architecture.
- Architect pack does not invent product scope.
- Answer pack does not answer unresolved human-owned questions.
- Proxy dry-run must block on unresolved answer-pack questions.

## MAP

- Charlie Munger (CH): proxy answers depend on Product/Architect inputs; missing role outputs can break downstream SpecKit artifacts.
- Occam's Razor (OM): split role packs before adding real execution.
- Richard Feynman (FE): user stories and open questions must be visible as artifacts.
- Karl Popper (PO): tests must falsify missing answer pack and blocking questions.
- Immanuel Kant (KT): every future SpecKit phase should consume the same answer-pack contract.
- Saffi (SH): speed vs. safety; safety dominates until human-owned questions are explicit.

## STABILIZED ISSUES

### Issue 1 - use cases/user stories are not formal enough for SpecKit

Root cause: use-case/API map is broad; SpecKit needs product-facing stories and criteria.

Action: add `build_speckit_product_manager_pack.py`.

Verification: `tests/test_speckit_pm_arch_answer_pack.py`.

### Issue 2 - architecture questions are mixed into generic open questions

Root cause: API/data/dependency/constitution questions need Architect ownership.

Action: add `build_speckit_architect_pack.py`.

Verification: architecture open question tests.

### Issue 3 - proxy can proceed without an answer-prep gate

Root cause: dry-run checked prework approval but not answer-pack readiness.

Action: add `build_speckit_answer_pack.py` and patch proxy dry-run to require it.

Verification: proxy test coverage updated.

## HANDLED

- Product Manager pack added.
- Architect pack added.
- SpecKit answer pack added.
- Escalation queue added.
- Proxy dry-run blocks missing/blocked answer pack.

## CONFLICTS

### Real SpecKit execution

- thesis: answer pack makes execution possible
- antithesis: answer pack may still contain blocking human questions from real HLDs
- safe recommendation: run smoke and inspect answer pack before implementing real execution
- decision needed: approve one-phase real execution only after answer pack is READY on a real HLD
