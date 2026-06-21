# HLDspec Engineering Quality Gates

**Status:** active governance policy for implementation work **on the HLDspec repo**.

## Purpose & audience

These gates govern how agents and contributors **change the HLDspec repo itself** —
the engineering practice required to land a change safely. They make the informal
"tests first / surgical edits" rules in `CLAUDE.md` and `AGENTS.md` explicit and
citable, and they operationalize the RunSkeptic framework's evidence/fail-closed
stance for everyday PRs.

This is **not** the target-software engineering doctrine. Guidance HLDspec injects
into a *target* product (hexagonal architecture, design-for-testability, stage-safe
testing, …) lives in [`ENGINEERING_TOOLBOX.md`](ENGINEERING_TOOLBOX.md) and
[`SOFTWARE_DESIGN_PRINCIPLES.md`](SOFTWARE_DESIGN_PRINCIPLES.md). Keep the two
separate: this doc is about building HLDspec; the toolbox is about what HLDspec
helps others build.

To avoid a second source of truth (see **EQG-12**), this policy **references**
rather than restates:
- artifact **ownership** → [`ANTI_DRIFT_CONTRACTS.md`](ANTI_DRIFT_CONTRACTS.md) Contract 2 (canonical);
- RunSkeptic **evidence fields** → [`RUNSKEPTIC_EVIDENCE_QUALITY.md`](RUNSKEPTIC_EVIDENCE_QUALITY.md);
- **legacy-test** protection → [`TEST_STRATEGY_V2.md`](TEST_STRATEGY_V2.md);
- **enforcement status** of each principle → [`HLDSPEC_PRINCIPLE_ENFORCEMENT_MATRIX.md`](HLDSPEC_PRINCIPLE_ENFORCEMENT_MATRIX.md).

## Keyword conventions

- **MUST** / **MUST NOT** — hard gate. A PR that violates it is `ACTION` or
  `CONFLICT`, never `PASS`, until fixed or an exception is documented where allowed.
- **SHOULD** — strong default; deviation requires a stated reason in the report.

## Definitions

**Behavior-changing code** — a change that alters observable output, control flow,
state, exit codes, file/artifact **content or location**, or contract behavior.
**Not** behavior-changing: docs, comments, pure renames with no behavior change,
formatting, test-only additions, and dependency bumps with no behavior change.
**When unsure, treat the change as behavior-changing.**

**Enforcement tags** (per gate, honest about *how* it is checked, per the
enforcement-matrix rule that an unenforced principle is "documentation only"):
- *test/gate* — a `tests_v2/` test or an approval/promotion gate enforces it;
- *receipt* — enforced by the RunSkeptic receipt / final report (reviewer-checkable evidence);
- *judgment* — reviewer/RunSkeptic judgment; no automation claimed.

---

## The gates

### A. Test & evidence discipline

**EQG-1 — TDD / regression evidence (MUST).** For behavior-changing code, a failing
test or characterization test MUST exist **before or with** the implementation. The
final report MUST identify the test that was **red before** and **green after** the
change. *Exception:* if TDD is genuinely impractical, the report MUST state the
documented reason **and** provide alternative evidence (characterization test,
recorded manual reproduction). A bare "TDD not applicable" is not acceptable.
*Enforcement: receipt.*

**EQG-2 — Regression test for every bug fix (MUST).** Every bug fix MUST add a
regression test that **would have failed before** the fix and passes after.
*Enforcement: receipt.*

**EQG-3 — Characterization before refactor (MUST).** Before refactoring existing
behavior, add or identify characterization tests that lock the current behavior. A
refactor MUST NOT change behavior unless the behavior change is explicitly approved
(and then it is no longer "just a refactor" — see EQG-1/EQG-6). *Enforcement: receipt.*

**EQG-4 — No test weakening (MUST NOT).** Agents MUST NOT delete, skip, loosen, or
rewrite a test to make it pass. The only exception: the test is **proven wrong**, and
the report documents *why* it was wrong and what replaced it. Legacy tests follow the
stronger-replacement rule in `TEST_STRATEGY_V2.md`. *Enforcement: receipt + test
(legacy-deletion convention); reviewer judgment for loosening.*

### B. Change discipline

**EQG-5 — Smallest safe slice (MUST).** Patch only the smallest coherent slice that
closes the named gap. MUST NOT bundle adjacent cleanup, architecture changes, or
opportunistic fixes. *Enforcement: judgment.*

**EQG-6 — Contract-first changes (MUST).** If behavior changes a journey boundary,
artifact location, approval rule, authority model, or ownership rule, the governing
contract MUST be updated **first or in the same PR**. Code MUST NOT silently redefine
a contract. *Reconciliation with EQG-5:* a behavior change **and the contract it
requires** are **one coherent slice** — the contract update is not "adjacent cleanup."
Bundling means *unrelated* work, not the contract the change depends on.
*Enforcement: receipt + test (anti-drift tests guard protected contracts).*

**EQG-7 — Compatibility / migration (MUST).** When changing paths, schemas, state, or
artifact layout, the change MUST preserve legacy behavior **or** provide an explicit
migration / fail-closed rule. **Silent fallback is forbidden.** *Enforcement: receipt
+ test (migration/legacy paths must be tested).*

**EQG-11 — Sensitive-area scan before patching (MUST).** Before patching, identify
which sensitive paths the change touches and say so in the report: path resolution,
state ownership, authority transitions, writes/deletes, external command execution,
approvals, compatibility boundaries. *Enforcement: receipt (RunSkeptic Fundamental
Scan).*

**EQG-12 — Single source of truth (MUST NOT).** Do not create parallel resolvers,
duplicate state readers, or competing path/ownership rules. Introduce or reuse **one**
named resolver/contract and route relevant read/write paths through it. *Enforcement:
receipt + test (e.g. the source-package pointer-aware resolver, PR #30).*

### C. Safety, state & ownership

**EQG-8 — Fail closed on ambiguity (MUST).** When state is ambiguous, split, stale, or
contradictory, stop with an explicit blocker. MUST NOT guess, repair, or silently
choose one side. *Enforcement: test (e.g. the split-brain blocker, PR #30) + receipt.*

**EQG-9 — Read-only proof (MUST).** Inspection / status / driver commands MUST be
read-only by default. Tests MUST prove no target mutation, no helper execution, and no
generated-artifact mutation where applicable. *Enforcement: test (no-mutation /
no-execution assertions).*

**EQG-13 — Idempotence (SHOULD).** Repeated runs SHOULD produce the same result or fail
with a clear reason. Re-running MUST NOT duplicate artifacts, corrupt state, or advance
workflow state unexpectedly. *Enforcement: receipt; test where a re-run path exists.*

**EQG-14 — Explicit artifact ownership (MUST).** Every artifact MUST have a declared
owner — HLDspec control plane, SpecKit runtime, human-authored source, generated
mirror, or target product code — and ownership determines where it may live and who
may mutate it. The **canonical owner map is `ANTI_DRIFT_CONTRACTS.md` Contract 2**;
this gate requires citing it, not restating it. *Enforcement: test (anti-drift) +
receipt.*

**EQG-15 — Observability before automation (MUST).** Before automating a transition,
first expose its status, evidence, blockers, and next safe action; automation may only
follow once the status path is proven. *Enforcement: judgment + receipt.*

### D. Reporting

**EQG-10 — Evidence-based final report (MUST).** Every implementation report MUST
include: changed files; tests run (with counts); red→green or characterization
evidence (EQG-1); known remaining gaps; and explicit boundary confirmations (what was
*not* touched). The shape used in recent PR bodies (e.g. PR #30) is the reference
template. *Enforcement: receipt.*

---

## Enforcement honesty

Per `HLDSPEC_PRINCIPLE_ENFORCEMENT_MATRIX.md`: a gate with no test and no automated
enforcement is **documentation-only** and a PR relying solely on it for a quality
claim is at most `ACTION`, not `PASS`. Several gates above are currently
**receipt-** or **judgment-**enforced. Promoting them to machine enforcement (a
matrix row + a `tests_v2/` test, e.g. a lint that fails a behavior-changing PR with no
red→green evidence) is tracked follow-up work, not part of this policy slice.

These gates are **not** added to `ANTI_DRIFT_CONTRACTS.md` in this slice; promoting
them to a protected anti-drift contract would invoke that doc's change-policy and is a
deliberate future step.

## See also

`CLAUDE.md` · `AGENTS.md` · `skeptic.md` (RunSkeptic) ·
[`HLDSPEC_QUALITY_REQUIREMENTS.md`](HLDSPEC_QUALITY_REQUIREMENTS.md) (product output
quality) · [`AGENT_ARTIFACT_HYGIENE.md`](AGENT_ARTIFACT_HYGIENE.md) (where artifacts live).
