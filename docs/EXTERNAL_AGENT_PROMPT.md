# External Agent Prompt: Human-in-the-Loop HLDspec Work

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

## Context budget rules

Large HLDs must be handled with bounded context.

Use shell tools such as `grep`, `rg`, `sed -n`, `awk`, `wc`, `head`, and `tail` to inspect files locally. Do not paste a whole large HLD into the agent context.

When converting a raw HLD:

- preserve `HLD.raw.md`
- edit only the working `HLD.md`
- convert in bounded batches of 3-5 major sections
- for very large candidate sections, inspect internal headings first
- explain each batch before editing
- after each batch, report changed sections, metadata chosen, refs added, uncertain fields, and a diff summary
- let the human steer or stop before the next batch

Safe local processing is allowed. The restriction is on model context and silent large rewrites, not on using `grep`, `sed`, or scripts.


## Judge/orchestrator and chunking rules

The main agent is the judge/orchestrator. It may use subagents, but only as bounded workers on specific chunks.

The judge/orchestrator remains responsible for briefing subagents, limiting their context, reviewing their output, keeping a compact running summary, synthesizing the result, and escalating unresolved decisions to the human.

Subagents do not own final decisions. The human owns unresolved decisions.

Use chunks instead of heavy token measurement.


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
