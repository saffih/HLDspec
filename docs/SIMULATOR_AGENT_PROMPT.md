Read `~/HLDspec/docs/LIMITED_AGENT_RUN_CARD.md` first.

Use `~/HLDspec` to process `./Simulator-System-HLD.md`.

Keep me in the loop. Before each major step, explain what you see, what it means, what you plan to do, the exact command/edit, expected result, and whether a human decision is needed. After each step, report what happened, files changed, what it means, and the next decision.

Do not paste the whole HLD into context. Use bounded local inspection with grep/rg/sed/awk/wc. Preserve the original HLD. Edit only the working copy in `.hldspec-first-run`.

Start with:

```bash
HLD="./Simulator-System-HLD.md"
WORK="$PWD/.hldspec-first-run"
~/HLDspec/scripts/first_run_readonly.sh "$HLD" "$WORK" --force
```

If exit code is 2, summarize `.hldspec-first-run/HLD_CONVERSION_PROMPT.md` and convert `.hldspec-first-run/HLD.md` in batches of 3-5 major sections. After each batch, show what changed and wait if interpretation is involved.

Stop before creating/modifying specs, target constitution, downstream artifacts, implementation files, or accepting DECOMPOSE/CONFLICT/SPLIT_PLANNED_SPEC/RESOLVE_CONFLICT as safe.
