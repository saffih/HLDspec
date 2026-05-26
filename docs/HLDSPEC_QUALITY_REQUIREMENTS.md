# HLDspec Quality Requirements

## Purpose

HLDspec quality is measured by whether users and agents can safely decide the
next step from explicit evidence.

## User UX

- The user should start with the public facade commands.
- Output must say what is blocked, what is safe, and what to do next.
- Human-owned decisions must be visible and must not be answered silently.
- Internal script names may appear only as maintainer/debug tools or report
  evidence, not as the primary user workflow.

## Agent UX

- Agents need stable sections, report paths, and PASS/ACTION/CONFLICT wording.
- Agents must be able to find current state, blockers, open questions, and next
  safe action without parsing prose paragraphs.
- Agent output must distinguish blocking review material from optional context.

## Output Quality

- Prefer deterministic headings and concise bullets.
- Include report paths when a report controls a decision.
- Use `none` for empty blocker or question lists.
- Do not hide missing required artifacts inside long file listings.

## Safety

- Source HLD/resources are read-only.
- Target-product durable state belongs under `target/`.
- SpecKit is not invoked until explicit approval gates pass.
- HLDspec does not manually create final SpecKit artifacts.
- Implementation requires explicit human approval.
- ACTION and CONFLICT findings block promotion/readiness.

## Testing

- User-facing output sections are regression-tested.
- Source HLD immutability is tested for flows that read a source HLD.
- Validators and promotion gates must write JSON and Markdown reports.
- Exit code behavior is part of the contract.

## Promotion and Readiness Gates

- Promotion requires a PASS promotion gate.
- Readiness marks above 7 require tests or reproduced evidence.
- Validator ACTION or CONFLICT findings block promotion.
- Missing RunSkeptic status for promoted capabilities blocks readiness.
- Unresolved human checkpoints are CONFLICT, not PASS.
