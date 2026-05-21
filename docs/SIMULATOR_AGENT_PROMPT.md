Read these first:

```text
~/HLDspec/docs/LIMITED_AGENT_RUN_CARD.md
~/HLDspec/docs/CHUNKED_AGENT_PROTOCOL.md
```

Use `~/HLDspec` to process:

```text
./Simulator-System-HLD.md
```

You are the judge/orchestrator.

Use subagents only as bounded workers on specific chunks. You remain responsible for briefing them, limiting their context, reviewing their output, synthesizing the result, and escalating unresolved decisions to the human.

Do not paste the whole HLD into context. Use bounded local inspection with `grep`, `rg`, `sed -n`, `awk`, and `wc`.

Start with:

```bash
HLD="./Simulator-System-HLD.md"
WORK="$PWD/.hldspec-first-run"
~/HLDspec/scripts/first_run_readonly.sh "$HLD" "$WORK" --force
```

Before each major step, report:

```text
What I see:
What it means:
What I plan to do:
Command or edit:
Expected result:
Human decision needed:
```

After each major step, report:

```text
What happened:
Files created or changed:
What it means:
Next decision:
```

If exit code is 2, summarize `.hldspec-first-run/HLD_CONVERSION_PROMPT.md` and convert `.hldspec-first-run/HLD.md` in chunks:

```text
Normal chunk: 1 major HLD section
Small-section batch: 3-5 major sections when sections are small enough
Large section: process alone
Very large section: inspect internal headings first
```

After each chunk, report changed sections, metadata chosen, refs added, uncertainty, and diff summary.

Stop before creating/modifying specs, target constitution, downstream artifacts, implementation files, or accepting `DECOMPOSE`, `CONFLICT`, `SPLIT_PLANNED_SPEC`, or `RESOLVE_CONFLICT` as safe.


Stop for human decision before accepting `DECOMPOSE`, `CONFLICT`, `SPLIT_PLANNED_SPEC`, or `RESOLVE_CONFLICT`, or before creating/modifying specs, target constitution, downstream artifacts, or implementation files.
