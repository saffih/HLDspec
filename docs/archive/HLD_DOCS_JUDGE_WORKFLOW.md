# HLD Docs Judge Workflow

This is a Skeptic-derived orchestration workflow for improving HLDs for documentation projects. It is not the base HLD format. Use `HLD_FORMAT.md` for the parseable HLD structure and `HLD_GENERATION.md` for the lightweight generation prompt.

When invoked, refresh the available Skeptic framework from the configured local checkout or source of truth, then treat that refreshed framework as authoritative. This document summarizes the expected core method:

```text
GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN
```

The Judge extends that method by orchestrating bounded reviewers or subagents so the main context stays small, evidence-backed, and reversible.

## Use for

- docs portals
- generated docs
- AI-assisted docs
- translation workflows
- internal knowledge bases
- API and developer docs
- docs publishing pipelines

## Workspace mode

Default mode is `DRAFT_ONLY`.

The Judge may create or update draft HLD workflow artifacts. Use `READ_ONLY` when the user says `RO`, `read only`, `review only`, `no edits`, `no file changes`, `inspect only`, or `analyze only`.

Do not implement code unless explicitly requested. Do not change protected files or perform protected actions without explicit approval.

Protected actions include:

- delete, rename, or reorganize files
- edit `AGENTS.md`
- edit CI/CD config
- edit source code
- edit production config
- overwrite published docs
- publish docs
- update search indexes
- remove links, redirects, or stale docs
- move internal or private content into public docs
- accept risk or approve release for a human owner

Before any protected action, report:

| Protected Action | File/Area | Reason | Risk | Verification | Revert Plan | Approval Needed |
|---|---|---|---|---|---|---|

## Environment diagnostic

Before starting, the Judge declares the actual environment instead of assuming one:

| Capability | Status | Notes |
|---|---|---|
| Real independent subagents available? | YES/NO | Name available mechanism if present. |
| Simulated isolated reviewers used? | YES/NO | Use when real subagents are unavailable or unnecessary. |
| Project files/repo access available? | YES/NO | Name inspected workspace. |
| Web/tool research available? | YES/NO | Use only when needed and allowed. |
| Workspace mode | DRAFT_ONLY/READ_ONLY/EDIT_ALLOWED | Explain why. |
| Cost constraints known? | YES/NO | State user-provided constraints. |
| Reviewer model/tool choice | DIAGNOSTIC | Prefer cheap/basic reviewers suitable for the task; do not use costly tools unless the user explicitly approves or the risk justifies asking. |

If real subagents are unavailable, simulate isolated reviewers sequentially. Do not claim simulated reviewers are truly independent. Keep reviewer findings separate until stabilization.

## Gate

Apply the Skeptic Gate.

Proceed only when:

- DONE is testable
- scope is tractable
- wrong-answer cost is acceptable

Output one:

- `PROCEED`
- `DECOMPOSE`
- `STOP`
- `CONFLICT`

Gate questions:

- What project is being designed?
- What must the HLD decide?
- Is DONE testable?
- Is scope tractable?
- What evidence/tools are available?
- Which decisions require humans?
- Which workflow depth applies?

## Workflow depth

Use the smallest mode that can produce a trustworthy result:

- `LIGHT`: small or low-risk. Gate, evidence, focused review, decision pack, draft HLD.
- `STANDARD`: default. Gate, evidence discovery, Fundamental Scan, Map, reviewers, Confidence, Stabilize, Judge, draft HLD.
- `FULL`: risky or important. Standard plus alternative strategies, scoring, reusable prompts, and suggested governance rules.

Upgrade to `FULL` when there is AI-generated content, publishing automation, source-of-truth ambiguity, unclear ownership, privacy/security risk, high wrong-answer cost, or irreversible rollout impact.

## Evidence discovery

Inspect available sources before rewriting:

- `README`
- docs folder
- docs config
- build or publish scripts
- CI workflows
- contribution guide
- `AGENTS.md`
- ADRs, HLDs, or architecture docs
- schemas and API contracts
- generated docs
- examples
- tests and evals
- prompts and AI workflows
- issue or PR templates
- release notes

Report only evidence that was inspected:

| Source | What It Proves | Reliability | Limitation |
|---|---|---|---|

Do not claim evidence from a file, tool, or source that was not inspected.

## Research summary

Before rewriting, summarize:

- project purpose
- target users
- docs structure
- source of truth
- ownership signals
- build/publish flow
- AI/prompt/generation flow, if any
- review/approval flow
- quality gates
- known gaps
- unclear areas
- likely human decisions

## Fundamental Scan

Apply the Skeptic Fundamental Scan before broad detection.

Detect only; do not fix.

Check:

- system purpose
- architecture shape
- boundaries
- ownership
- source of truth
- main flows
- interfaces and coupling
- high-risk, recent, or suspected areas
- verification path
- rollback path

Clean scan is not proof of safety. Structural issues outrank local fixes. Downstream findings are provisional if fundamentals may invalidate them.

## Map findings

Apply the Skeptic Map phase. Record findings before deciding.

For each meaningful entity, ask:

- What is this?
- What is it for?
- What depends on it, and what does it depend on?
- What must always be true?
- What breaks it?
- How do we know it works?

Apply structural checks:

- role and ownership
- boundaries and concern split
- interfaces, required links, forbidden links, implicit links, contracts
- necessary vs accidental coupling
- source of truth and competing copies
- data/control flow, update timing, consumers
- reversibility, retry safety, and failure signal

Apply the Skeptic thinkers selectively but explicitly:

- Charlie Munger (CH): dependency, downstream failure, bounded failure
- Occam's Razor (OM): necessity, simplicity, boundary clarity
- Richard Feynman (FE): truth now, explanation, verification
- Karl Popper (PO): falsification, contradiction, silent failure
- Immanuel Kant (KT): universal pattern safety
- Saffi (SH): real forces, integration vs compromise, explicit conflict

## Public/private boundary

Classify sources and outputs:

| Source/Output | Public/Internal/Private | Allowed Use | Risk | Required Control |
|---|---|---|---|---|

Rules:

- Internal/private sources must not flow into public docs unless approved and sanitized.
- Search indexes are publishable artifacts and follow the same privacy rules as docs pages.
- Public docs, internal runbooks, release notes, and search indexes are separate surfaces.

## Reviewer passes

Run real subagents when available and useful. Otherwise simulate isolated reviewers sequentially.

The Judge chooses cheap/basic reviewer agents or models appropriate to the task and context budget. If a costly model, tool, or external service seems necessary, ask for explicit approval with the reason and expected value.

Potential reviewers:

- Documentation Architecture
- Product/User Journey
- Source-of-Truth and Governance
- AI/Automation
- Reliability and Operations
- Evaluation and Quality
- Complexity and Maintainability
- Human Escalation

Each reviewer reports:

- strongest findings
- missed risks
- likely false positives
- evidence labels
- recommended HLD changes
- verification gaps
- human decisions required
- confidence score from 1 to 5

Do not merge reviewer findings yet.

## Confidence

Apply the Skeptic Confidence phase before stabilization and decisions.

Check:

- Fundamental Scan completed
- Universal Questions applied
- Structural Checks applied
- relevant thinkers considered
- important conclusions have evidence
- unknowns and skipped areas are listed
- owner/source-of-truth/contract/dependency unknowns are explicit
- test path, revert path, and acceptance criteria are known or marked unknown

If confidence is weak, expand Map only where evidence requires it. If confidence cannot reasonably improve, return `CONFLICT`.

## Stabilize

Do not decide on raw findings.

Merge findings sharing:

- data, boundary, responsibility, interface
- source of truth, failure mode, root cause

Classify root cause:

- local bug
- missing test
- missing contract
- unclear ownership
- source-of-truth issue
- accidental coupling
- stale assumption
- systemic rule issue
- detection confidence issue

Output:

| Issue | Root Cause | Evidence Level | Affected Areas | Decision Path |
|---|---|---|---|---|

Do not convert `CONFLICT` into `FIX`.

## Evidence labels

Use Skeptic evidence levels as the primary labels:

- `OBSERVED`: directly seen in code, tests, config, docs, or runtime behavior.
- `REPRODUCED`: confirmed with a failing test, probe, command, or execution.
- `HISTORICAL`: confirmed by issue, changelog, advisory, maintainer note, release note, or incident.
- `INFERRED RISK`: plausible from structure, boundary, exposure, missing tests, or weak evidence, but not reproduced.

Optional source-specific labels may be used as notes, but they map back to Skeptic evidence:

- `TOOL_OBSERVED` maps to `OBSERVED`.
- `DOC_OBSERVED` maps to `OBSERVED`.
- `TOOL_CONFLICT` maps to `OBSERVED` plus a conflict note.
- `TOOL_MISSING` maps to `OBSERVED` plus a missing-evidence note.
- `ASSUMPTION`, `TBD`, `CONFLICT`, and `NEEDS_VERIFICATION` are not proof.
- `EXEMPLAR` marks a good pattern to preserve.

Never report `INFERRED RISK` as a confirmed bug. `FIX` requires `OBSERVED` evidence and a verification path.

## Decide

Apply Skeptic Decide criteria.

Use:

- `FIX`: safe direct improvement with clear source of truth, adequate confidence, reversibility, and verification.
- `DECOMPOSE`: scope/risk is high but structure is clear enough to split safely.
- `CONFLICT`: owner, source of truth, approval authority, product intent, risk acceptance, reversibility, or evidence is unclear.
- `TBD`: missing information.
- `LEARN`: candidate governance or `AGENTS.md` rule.

Do not ask vague questions. Escalate with:

| Decision | Why Human Needed | Options | Trade-off | Recommended Default | Blocking? |
|---|---|---|---|---|---|

## Act safely

Act only after `DECIDE` says `FIX`.

For this workflow, action normally means editing the draft HLD or workflow artifact. Code, CI, production config, publishing, search indexes, and `AGENTS.md` remain protected.

For each accepted HLD change, include:

- what changed
- why it changed
- which Skeptic check, thinker, or reviewer motivated it
- verification path

Use the trace pattern:

```text
<thinker/check> found <issue>, so we changed <HLD area>.
```

## Verify

Use evidence, not confidence.

Check:

- end-to-end trace from evidence to HLD claim
- 3-5 manual spot checks when practical
- constraints: correctness, safety, performance, cost, context, maintainability
- pre-mortem: 3 concrete failure modes addressed
- regression: previously working docs behavior still works
- known-bad or edge case when results are suspiciously clean

Separate:

- structural validation: build, links, formatting, generated files
- semantic validation: correctness, meaning, terminology, source fidelity
- governance validation: ownership, approval, rollback authority

Structural validation does not substitute for semantic or governance validation.

## Prompt files as governed artifacts

Treat prompt files as governed artifacts when they affect generated documentation.

For prompt changes, require:

- owner
- reviewer
- sample output validation
- rollback path
- regression check against known-bad cases

## Final HLD shape

When producing a final improved HLD for a docs project, prefer:

Use the parseable format from `HLD_FORMAT.md`: each major section should be written as `## HLD-xxx - Title` with the required `HLD-*` metadata block. The topics below are suggested section responsibilities, not literal unnumbered headings.

1. Executive Summary
2. Goals
3. Non-Goals
4. Current Project Reality
5. Problem Statement
6. Proposed Documentation Architecture
7. Information Architecture
8. Content Lifecycle
9. Source of Truth and Governance
10. Public/Private Content Boundary
11. Tooling and Automation
12. AI Usage, if relevant
13. Review and Quality Gates
14. Reliability and Operations
15. Rollback Plan
16. Risks
17. Open Questions
18. Design Decisions
19. Verification Plan
20. Rollout Plan
21. Human Decision Pack
22. HANDLED
23. CONFLICTS
24. Verify

For `HANDLED`, include evidence level and verification path. For `CONFLICTS`, include missing evidence and the specific decision needed.

## Final status

Use one:

- `WIP`: work incomplete or verification missing
- `FINAL_CANDIDATE`: no known blocking issues after verification
- `BLOCKED`: cannot proceed safely
- `CONFLICT`: human decision required
- `EDITED_AND_VERIFIED`: files changed and verification passed
- `EDITED_NEEDS_VERIFICATION`: files changed but verification incomplete

Every completed task ends with status `HANDLED` or `CONFLICT`. Reports may include `HANDLED` and `CONFLICTS` sections.

## Final self-check

| Check | Pass/Fail | Notes |
|---|---|---|
| Gate completed |  |  |
| Workspace safety preserved |  |  |
| Environment diagnostic completed |  |  |
| Evidence sources listed |  |  |
| Research completed before rewrite |  |  |
| Findings mapped before decisions |  |  |
| Reviewer findings kept separate before stabilization |  |  |
| Findings stabilized by root cause |  |  |
| Detection confidence checked |  |  |
| Evidence labels applied |  |  |
| Human-owned decisions escalated |  |  |
| No unresolved CONFLICT converted into ACTION |  |  |
| Every accepted change has verification |  |  |
| No protected action taken without approval |  |  |
| HANDLED includes evidence and verification |  |  |
| CONFLICTS include missing evidence and decision needed |  |  |
| Cost/tool constraints followed |  |  |
| Skeptic flow applied |  |  |
