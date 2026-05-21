# External Agent Prompt: Human-in-the-Loop HLDspec Work

made by AI

Use this prompt when running an agent from another project directory, for example from the simulator repo.

## Prompt

Read the HLDspec repository first:

```text
~/HLDspec/AGENTS.md
~/HLDspec/README.md
~/HLDspec/HLD_FORMAT.md
~/HLDspec/HLD_GENERATION.md
~/HLDspec/docs/FIRST_RUN.md
~/HLDspec/docs/TARGET_SPEC_CONTEXT.md
```

Goal:

Use `~/HLDspec` to assess and process the project HLD in this repository.

Communication rules:

1. Keep the human in the loop throughout the work.
2. Before each major step, explain:
   - what you see
   - what you think it means
   - what you are about to do
   - the exact command or file edit you plan to use
   - what output or decision you expect
3. After each major step, report:
   - what happened
   - what files were created or changed
   - what the result means
   - whether a human decision is needed
4. Stop and ask for a decision when:
   - source-of-truth is unclear
   - a conversion boundary is unclear
   - HLD sections may need splitting
   - an API/interface contract is ambiguous
   - data/state ownership is ambiguous
   - performance/memory constraints are unclear
   - failure/recovery behavior is unclear
   - a command would write specs, target constitution, downstream artifacts, or implementation files
   - the next step could lock in a design decision
5. Do not silently continue through unresolved conflicts.
6. Do not hide uncertainty. Mark uncertainty as `TBD`, `CONFLICT`, or an explicit question.
7. Prefer small observable steps over large hidden work.
8. The human may interrupt or steer after any update.

First action:

Detect whether the HLD is already in HLDspec format or needs conversion.

Use:

```bash
~/HLDspec/scripts/first_run_readonly.sh "<path-to-HLD.md>" "<workspace>" --force
```

Explain the result:

- If the HLD needs conversion, open and summarize `HLD_CONVERSION_PROMPT.md`.
- If the HLD is ready, open and summarize `spec_build_plan_review.md`.

Do not assume one HLD section becomes one spec.

The correct model is:

```text
HLD sections
-> HLD map
-> Spec Build Plan
-> planned spec references related full HLD sections
-> one focused target spec later
```

Do not generate target specs yet unless HLDspec has implemented and tested that command and the human explicitly approves.
