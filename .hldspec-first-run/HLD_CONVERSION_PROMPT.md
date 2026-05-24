# HLD Conversion Prompt

made by AI

The input HLD is not yet in HLDspec format.

Detected:

- existing HLDspec sections: 0
- candidate major sections: 36
- large candidate sections: 3
- conversion plan status: STOP_SPLIT_DECISION_REQUIRED

Use the format report and conversion plan:

```text
/Users/saffi/code/HLDspec/.hldspec-first-run/logs/hld_spec_sync/20260523-203125/hld_format_report.md
/Users/saffi/code/HLDspec/.hldspec-first-run/logs/hld_spec_sync/20260523-203125/suggested_hld_sections.json
/Users/saffi/code/HLDspec/.hldspec-first-run/.specify/sync/hld_conversion_plan.md
/Users/saffi/code/HLDspec/.hldspec-first-run/.specify/sync/hld_conversion_plan.json
/Users/saffi/code/HLDspec/.hldspec-first-run/.specify/sync/hld_conversion_decision_queue.md
/Users/saffi/code/HLDspec/.hldspec-first-run/.specify/sync/hld_conversion_decision_queue.json
```

The conversion plan is the controlling artifact for chunk order and split stop decisions. The decision queue is the human checkpoint; do not convert while blocking questions are still TBD.

Task:

Convert:

```text
/Users/saffi/code/HLDspec/.hldspec-first-run/HLD.raw.md
```

into:

```text
/Users/saffi/code/HLDspec/.hldspec-first-run/HLD.md
```

Rules:

- Preserve original design content.
- Chunked judge/subagent rules:
  - The main agent is the judge/orchestrator and remains responsible for the final synthesis.
  - Subagents are bounded workers and do not own final decisions.
  - Use subagents only for specific chunks or focused checks.
  - Normal chunk: one major HLD section.
  - Small-section batch: 3-5 major sections when sections are small enough.
  - Large section: process alone.
  - Very large section: inspect internal headings first.
  - The judge/orchestrator keeps a compact running summary instead of accumulating the whole HLD.
- Context budget rules:
  - Do not paste the whole HLD into agent context.
  - Use local tools such as `grep`, `rg`, `sed -n`, `awk`, and `wc` for bounded inspection.
  - Convert in bounded batches of 3-5 major sections.
  - For very large candidate sections, inspect internal headings first and explain whether a split is needed.
  - Before each batch, state what sections you will edit and why.
  - After each batch, report changed sections, metadata chosen, refs added, uncertain fields, and a concise diff summary.
  - Let the human steer or stop before the next batch when interpretation is involved.
- Create stable major HLD sections: `## HLD-001 - Title`, `## HLD-002 - Title`, etc.
- Add required metadata under each major section:
  - `HLD-ID`
  - `HLD-ROLE`
  - `HLD-STATUS`
  - `HLD-RISK`
  - `HLD-SPECS`
  - `HLD-RESOURCES`
  - `HLD-VERIFY`
- Use `HLD-SPECS: TBD` unless a mapping is certain.
- Use `HLD-RESOURCES: TBD` unless resources/interfaces/contracts are explicit.
- Add `DEPENDS REF HLD-xxx`, `REF HLD-xxx`, or `CONFLICTS_WITH REF HLD-xxx` only when supported by the text.
- Do not create specs.
- Do not create `.specify/memory/constitution.md`.
- Do not generate implementation files.
- Do not invent architecture decisions.
- Split very large candidate sections only when they contain several independent design responsibilities.

After conversion, run:

```bash
bash scripts/first_run_readonly.sh "/Users/saffi/code/HLDspec/.hldspec-first-run/HLD.md" "/Users/saffi/code/HLDspec/.hldspec-first-run/firstrun" --force
```
