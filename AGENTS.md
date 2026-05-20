# Agent Instructions for HLDspec

made by AI

This repository contains wrapper tools for turning a High-Level Design document into Spec Kit artifacts and downstream planning or implementation artifacts.

Do not bypass the wrappers unless explicitly instructed.

## Core rule

`HLD.md` is the canonical source of truth.

Generated files under `.specify/sync/` are derived artifacts and may be regenerated.

Use the scripts in this repo to validate, sync, and process HLD-driven work.

## Main tools

Use these wrappers:

```bash
./hld_spec_sync.py
./hld_spec_downstream.py
```

Do not manually create or update specs, plans, tasks, or downstream artifacts when the wrapper can do it.

## HLD creation or improvement

When asked to create a new HLD, improve an HLD, or make an HLD workable for HLDspec:

1. Read `HLD_GENERATION.md`.
2. Use the format from `HLD_FORMAT.md`.
3. Keep one canonical `HLD.md`.
4. Use stable section headings:

```md
## HLD-003 - Section Title
```

5. Add required metadata under each major section:

```md
HLD-ID: HLD-003
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: 001,002
HLD-RESOURCES: hld_spec_sync.py,.specify/memory/constitution.md,specs/*/spec.md
HLD-VERIFY: related specs preserve HLD anchors; feature graph includes dependencies
```

6. Use inline section references:

```md
REF HLD-002
DEPENDS REF HLD-002
BLOCKED_BY REF HLD-009
CONFLICTS_WITH REF HLD-011
```

7. Do not renumber existing HLD IDs unless explicitly requested.
8. Mark unknown mappings as `TBD`; do not invent them.
9. Mark unresolved design conflicts as `CONFLICT` or `CONFLICTS_WITH REF HLD-xxx`.

## Existing huge HLD or raw HLD not in HLDspec format

Use this workflow when the user provides a large existing HLD that is not yet in HLDspec format, or asks to make an HLD workable for spec sync.

The goal is to make the HLD parseable and safe for bounded processing without destroying the original document.

### Case

Use this workflow when:

- the HLD is very large
- the HLD does not use `## HLD-xxx - Title` headings
- the HLD does not contain `HLD-*` metadata lines
- the HLD has implicit cross-section relationships
- the user asks to convert, prepare, normalize, or make the HLD usable by HLDspec
- the user wants to update specs from an existing HLD but `--hld-map-only` fails

### Required solution

Do not run full HLD-to-spec sync on an unformatted huge HLD.

Do not blindly rewrite the whole HLD.

Do this instead:

1. Preserve the original HLD.

```bash
cp <original-hld-file>.md HLD.raw.md
cp HLD.raw.md HLD.md
```

2. If `--hld-format-report` exists, run it first.

```bash
./hld_spec_sync.py --hld HLD.md --hld-format-report
```

Review:

```text
logs/hld_spec_sync/<timestamp>/hld_format_report.md
logs/hld_spec_sync/<timestamp>/suggested_hld_sections.json
```

This report is read-only. It should not modify `HLD.md`, call an agent, or write specs.

3. If `--hld-format-report` does not exist yet, use the grep fallback.

```bash
grep -nE '^(#|##|###) ' HLD.raw.md > /tmp/hld_headings.txt
cat /tmp/hld_headings.txt
```

4. Identify major sections only.

Do not tag every subsection. Use `HLD-xxx` IDs only for major design areas, such as:

- executive summary
- governance/source of truth
- architecture
- processing flow
- interfaces/contracts
- data/state
- failure modes/recovery
- testing/verification
- risks/open questions

5. Convert accepted major sections into HLDspec format.

```md
## HLD-003 - Section Title

HLD-ID: HLD-003
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

6. Use `TBD` instead of inventing mappings.

Unknown spec IDs, owners, resources, or source-of-truth decisions must be marked as `TBD`.

Do not guess.

7. Add inline references between sections where relationships are known.

```md
This section DEPENDS REF HLD-002 because governance defines what may be generated.

This section REF HLD-006 for rollback behavior.

This approach CONFLICTS_WITH REF HLD-011 because both define different ownership rules.
```

8. Validate the formatted HLD.

```bash
./hld_spec_sync.py --hld HLD.md --hld-map-only
```

Review:

```text
.specify/sync/hld_index.md
.specify/sync/hld_ref_map.json
.specify/sync/hld_sections/
```

Do not continue if map validation fails.

9. Run one bounded prompt before syncing.

```bash
./hld_spec_sync.py --hld HLD.md --use-hld-map --target-hld HLD-003 --prompt-only
```

Review:

```text
logs/hld_spec_sync/<timestamp>/context_selection.json
logs/hld_spec_sync/<timestamp>/prompt.md
```

10. Sync one target section at a time.

```bash
./hld_spec_sync.py --hld HLD.md --use-hld-map --target-hld HLD-003
```

11. Continue downstream only after the related spec exists.

```bash
./hld_spec_downstream.py --hld HLD.md --use-hld-map --target-hld HLD-003 --phase plan --prompt-only

./hld_spec_downstream.py --hld HLD.md --use-hld-map --target-hld HLD-003 --phase plan
```

### Do not

- Do not overwrite or delete `HLD.raw.md`.
- Do not tag every small subsection.
- Do not invent spec IDs, owners, resources, or source-of-truth decisions.
- Do not manually split the HLD into many canonical source files by default.
- Do not run full-HLD sync when `--use-hld-map --target-hld` is appropriate.
- Do not continue if `--hld-map-only` reports validation errors.
- Do not use auto-conversion or auto-chunk execution without first reviewing a report or chunk plan.

### Success criteria

The HLD is ready for HLDspec processing when:

- `HLD.raw.md` preserves the original.
- `HLD.md` has stable `## HLD-xxx - Title` major sections.
- each major section has required `HLD-*` metadata.
- cross-section relationships use `REF HLD-xxx`.
- `./hld_spec_sync.py --hld HLD.md --hld-map-only` passes.
- `hld_index.md` gives a useful overview of the design.
- one `--prompt-only --target-hld` run shows bounded context instead of the full huge HLD.


## Standard workflow

### 1. Validate HLD structure

```bash
./hld_spec_sync.py --hld HLD.md --hld-map-only
```

Review:

```text
.specify/sync/hld_index.md
.specify/sync/hld_ref_map.json
.specify/sync/hld_sections/<section-id>.md
```

Do not continue if the HLD map is invalid.

### 2. Review HLD-to-spec prompt

```bash
./hld_spec_sync.py --hld HLD.md --use-hld-map --target-hld HLD-003 --prompt-only
```

Review:

```text
logs/hld_spec_sync/<timestamp>/context_selection.json
logs/hld_spec_sync/<timestamp>/prompt.md
```

Confirm the prompt uses bounded HLD context and does not load the full HLD unnecessarily.

### 3. Run HLD-to-spec sync

```bash
./hld_spec_sync.py --hld HLD.md --use-hld-map --target-hld HLD-003
```

Review:

```text
.specify/sync/staged/<run-id>/proposed_writes.md
logs/hld_spec_sync/<timestamp>/run_summary.json
specs/<NNN-feature-slug>/spec.md
.specify/sync/spec_index.json
.specify/sync/feature_graph.json
```

### 4. Review spec-to-downstream prompt

```bash
./hld_spec_downstream.py --hld HLD.md --use-hld-map --target-hld HLD-003 --phase plan --prompt-only
```

Review:

```text
logs/hld_spec_downstream/<timestamp>/context_selection.json
logs/hld_spec_downstream/<timestamp>/prompt.md
```

### 5. Run downstream planning

```bash
./hld_spec_downstream.py --hld HLD.md --use-hld-map --target-hld HLD-003 --phase plan
```

Review:

```text
.specify/sync/downstream/gap_closure_plan.md
specs/<NNN-feature-slug>/plan.md
specs/<NNN-feature-slug>/research.md
specs/<NNN-feature-slug>/data-model.md
specs/<NNN-feature-slug>/quickstart.md
logs/hld_spec_downstream/<timestamp>/run_summary.json
```

## Resume behavior

Sync map-aware target runs support:

```bash
./hld_spec_sync.py --hld HLD.md --use-hld-map --target-hld HLD-003 --resume
./hld_spec_sync.py --hld HLD.md --use-hld-map --target-hld HLD-003 --restart-map-run
```

Downstream resume is not currently the default workflow unless implemented and documented.

For downstream, rerun the explicit target and phase:

```bash
./hld_spec_downstream.py --hld HLD.md --use-hld-map --target-hld HLD-003 --phase plan
```

## Safety rules

Do not directly edit these generated artifacts unless explicitly asked:

```text
.specify/sync/*
.specify/sync/downstream/*
specs/*/plan.md
specs/*/tasks.md
specs/*/research.md
specs/*/data-model.md
specs/*/quickstart.md
```

Prefer wrapper commands that generate or update them.

Do not write implementation files unless the user explicitly asks and the downstream command uses:

```bash
--allow-implementation --implementation-root <path>
```

Do not remove or rename HLD sections, spec directories, or generated metadata unless explicitly requested.

## Protected paths

Do not write to:

```text
.git/
.agents/
.codex/
logs/
```

Do not modify CI/CD, production config, or implementation code unless explicitly requested.

## Validation commands

Before finalizing script changes, run:

```bash
python3 -m py_compile hld_spec_sync.py hld_spec_downstream.py hld_map.py
PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 -m unittest discover -s tests -v
```

For docs-only changes, at minimum verify links and examples manually.

## Expected agent behavior

When asked to "create an HLD":

1. Use `HLD_GENERATION.md`.
2. Produce or update `HLD.md`.
3. Validate with `--hld-map-only`.

When asked to "make an HLD workable":

1. Convert it to the format in `HLD_FORMAT.md`.
2. Add stable `HLD-xxx` headings.
3. Add required `HLD-*` metadata.
4. Add inline `REF HLD-xxx` relationships.
5. Run `--hld-map-only`.

When asked to "update specs from HLD":

1. Validate the HLD map.
2. Run sync prompt-only first.
3. Review `context_selection.json` and `prompt.md`.
4. Run sync for the target HLD section.

When asked to "catch up downstream artifacts for the next feature":

1. Identify the target HLD section.
2. Validate the HLD map.
3. Run sync if specs are stale.
4. Run downstream prompt-only.
5. Run downstream phase `plan`, `tasks`, or `all` as requested.

## Do not

- Do not manually split `HLD.md` into many canonical HLD files by default.
- Do not bypass `hld_spec_sync.py` when updating specs from HLD.
- Do not bypass `hld_spec_downstream.py` when creating downstream Spec Kit artifacts.
- Do not load the whole HLD into prompts when `--use-hld-map --target-hld` is appropriate.
- Do not invent HLD IDs, spec IDs, owners, or source-of-truth decisions.
- Do not silently resolve conflicts; mark them as `TBD`, `CONFLICT`, or `CONFLICTS_WITH REF HLD-xxx`.
