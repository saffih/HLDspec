# Target Snapshot Hash Provenance Fix

Status: correction note for future Journey 0 dry-run evidence.

## What Was Found

Historical Flow dry-run reports included no-mutation hash receipts for target
files such as `README.md`, `HLD.md`, and `core.md`. Later review found that the
reported `README.md` and `HLD.md` hash values could not be revalidated against
the committed target history, target worktree, or workspace/source-package
copies available during the review.

This is a provenance-recording defect. It does not prove that the target files
were mutated during those dry runs.

## Affected Historical Receipts

Treat target hash rows in these historical reports as suspect unless they are
freshly revalidated from the exact approved target paths:

- `docs/journey0_real_target_dry_runs/flow-journey0-dry-run.md`
- `docs/journey0_real_target_dry_runs/flow-journey0-declared-evidence-dry-run.md`
- `docs/journey0_real_target_dry_runs/flow-journey0-corrected-declared-evidence-dry-run.md`
- `docs/flow_journey1_hld_hardening/flow-journey1-readiness-report.md`

The old reports remain historical receipts and are not rewritten by this note.

## Correct Rule Going Forward

Future no-mutation proofs must derive target hashes from the exact approved
target path bytes for the current run.

Each proof row must identify:

- target root
- relative path
- resolved target path identity
- source kind, such as `approved_target_file`
- before SHA-256
- after SHA-256
- whether bytes changed
- whether the hash source was the approved target path

Derived artifacts, source-package copies, workspace copies, and previous report
values may not be used as target no-mutation hashes. If those artifacts are
hashed, they must be labeled separately as derived evidence.

## Required Follow-Up Use

The next SDD-ready gate re-run must use the fixed target snapshot proof path and
must not rely on the affected historical hash receipts.

This note does not close J0-12 globally, does not authorize SpecKit, does not
wire commands, does not start Journey 2 or Journey 3, and does not create
backlog or implementation scope.
