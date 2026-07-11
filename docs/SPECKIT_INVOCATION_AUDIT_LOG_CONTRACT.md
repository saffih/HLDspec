# SpecKit Invocation Audit Log Contract

**Status: RATIFIED DESIGN CONTRACT. Runtime implementation: Slice A done, B–E NOT IMPLEMENTED.**
The design questions below are resolved; Slice A (path helper + schema
validator, `hldspec/speckit_invocation_audit.py`) is implemented — no code in
this repo implements the writer, reader, or CLI surfaces described below.
This doc resolves the open design questions recorded in
[`docs/HLDSPEC_DEVELOPMENT_BACKLOG.md`](HLDSPEC_DEVELOPMENT_BACKLOG.md) P1-019
and records a five-slice implementation plan (§9). Ratifying this contract
authorized no implementation slice by itself: the writer, runtime
integration, reader, CLI output, and `speckit_drive_loop.py` wiring each
still require their own separate gate before work starts.

This doc does not redefine the Driver/Toolchain vocabulary (owned by
[`TOOLCHAIN_DRIVER_CONTRACT.md`](TOOLCHAIN_DRIVER_CONTRACT.md)), the ownership
zones (owned by [`TOOLCHAIN_DRIVER_BOUNDARY.md`](TOOLCHAIN_DRIVER_BOUNDARY.md)),
or the evidence-provenance axis
(`DRIVER_OBSERVED` / `MANUAL_ATTESTED`, owned by
[`TOOLCHAIN_DRIVER_EVIDENCE_CONTRACT.md`](TOOLCHAIN_DRIVER_EVIDENCE_CONTRACT.md)).
It adds one axis those docs do not cover: **a durable, append-only record that
an external SpecKit invocation was attempted and what happened**, independent
of whether that invocation's evidence is later classified as
`DRIVER_OBSERVED`, `MANUAL_ATTESTED`, readiness evidence, or nothing at all.

## 1. Why this doc exists

Live invocation proof today lives only in point-in-time markdown records
(`docs/FIRST_LIVE_E2E_PROOF.md`, `docs/SPECKIT_INVOKER_TASKS_HAIKU_LIVE_PROOF.md`)
and `TASKS.md` status lines. Those are one-off snapshots written by hand after
the fact; nothing durable and queryable records every attempted invocation as
it happens. `docs/HLDSPEC_DEVELOPMENT_BACKLOG.md` P1-019 named this gap and
listed nine open design questions without answering them. This doc answers
those nine questions and defines the resulting contract.

## 2. Canonical storage

```text
control_paths.resolve_hldspec_dir(target) / "audit" / "speckit_invocations.jsonl"
```

Concretely, via `hldspec/control_paths.py:resolve_hldspec_dir`
(confirmed present, pointer-aware):

- normal mode: `target/.hldspec/audit/speckit_invocations.jsonl`
- external-controller mode (valid `.hldspec-run.json` pointer): `<controller>/.hldspec/audit/speckit_invocations.jsonl`

This makes the log HLDspec-owned control state that follows the same
pointer-resolution rule as every other control read/write (`control_paths.py`
module docstring: "so external-controller mode can never split state").

It must **not** live under `.specify/`, `specs/`, `.hldspec/source_package/`,
`.hldspec/runtime/`, `.hldspec/sync/`, the general `.hldspec/events.jsonl`, or
a repo-level docs directory:

- `.hldspec/runtime/` is vendored runtime-installation provenance, not
  invocation history.
- `.hldspec/events.jsonl` (`hldspec/workspace_adapter.py`) is general product
  event history and does not carry this log's redaction, retention, failure,
  and lifecycle contract.
- readiness evidence, development receipts, and proof records are separate
  categories (§8) with their own existing homes.

## 3. Format

- UTF-8, newline-delimited JSON (NDJSON): one complete JSON object per line.
- Append-only history. No array wrapper. No mutable "latest invocation"
  object.
- `schema_version: 1` on every record.
- No automatic rewriting, deletion, compaction, truncation, or repair by any
  writer or reader.

## 4. Invocation lifecycle

Each external invocation has one stable `invocation_id` (UUID string) and
normally produces two records sharing that ID: `STARTED`, then `FINISHED`.

**STARTED** must be durably appended and `fsync`ed before the external
command begins. If it cannot be written: do not invoke, return a blocking
audit error, do not consume an invocation budget, do not silently downgrade to
an unlogged run.

**FINISHED** is appended, using the same `invocation_id`, after the external
command returns or is terminated. It must be durably appended before the
attempt is reported as auditable, before any automatic drive-loop
continuation, and before audit continuity is treated as intact. If the
invocation completed but `FINISHED` cannot be written: do not retry the
invocation, preserve the actual invocation result separately, stop automatic
continuation, surface human attention, and leave the unmatched `STARTED`
record as durable evidence of an incomplete lifecycle.

An unmatched `STARTED` record means **INCOMPLETE / UNKNOWN COMPLETION** and
must never be interpreted as success.

## 5. Record fields

### 5.1 Common to STARTED and FINISHED

```text
schema_version        integer, 1
record_type           STARTED | FINISHED
invocation_id         UUID string, shared by the STARTED/FINISHED pair
recorded_at_utc        RFC3339 UTC timestamp ending in Z
helper_id              "speckit" (matches hldspec/helper_registry.py helper_id convention)
toolchain              "SpecKit"
execution_path         "speckit_invoker" (initial); "speckit_drive_loop" reserved,
                       see §9 Slice D — not authorized by this contract
runtime                runtime identity, e.g. "claude"
phase                  HLDspec phase identity
skill                  concrete installed skill identity, e.g. "speckit-tasks"
model                  routed model identity
authority_level        existing authority classification, normally
                       "EXECUTE_WITH_APPROVAL" (hldspec/helper_registry.py
                       AUTHORITY_EXECUTE_WITH_APPROVAL)
approval_ref           existing approval artifact/reference when available;
                       records authority, never grants it
target_binding         object, see §6
command_identity       object, see §7
```

### 5.2 `target_binding`

```text
target_path_sha256       sha256 of the normalized resolved target path
                         (never the raw absolute path)
binding_status           BOUND | SYNTHETIC | PARTIAL | UNAVAILABLE
git_branch_before        required when target is a git repo
git_head_before          required when target is a git repo
remote_identity_sha256   nullable when no remote exists
source_package_sha256    conditionally nullable
feature_id               conditionally nullable
spec_dir                 conditionally nullable
bundle_id                conditionally nullable
```

Rules: never persist the absolute target path. Null/absent values must never
be silently coerced into a stronger `binding_status`. Repeated production or
drive-loop reliance must not auto-continue with `binding_status: UNAVAILABLE`.

### 5.3 `command_identity`

```text
agent_cmd               safe command prefix (no prompt text)
argv_without_prompt      argv with the prompt text removed
prompt_sha256            hash of the exact prompt bytes used
prompt_bytes             byte length of the prompt
skip_permissions          bool
```

Rules: never persist the raw prompt, environment variables, credentials, or
tokens. The prompt must never appear inside `argv_without_prompt`.

### 5.4 STARTED-specific

```text
started_at_utc
git_signature_before_sha256
```

May include a bounded, non-sensitive preflight classification.

### 5.5 FINISHED-specific

```text
finished_at_utc
duration_ms
outcome                  SUCCESS | COMMAND_FAILED | HOLLOW_COMPLETION |
                         TIMEOUT | INTERRUPTED | UNEXPECTED_MUTATION
returncode               (matches InvocationResult.returncode, hldspec/speckit_invoker.py)
ok                       (matches InvocationResult.ok)
produced_artifacts        (matches InvocationResult.produced_artifacts —
                         the existing anti-hollow-completion signal)
verified                  must reflect existing anti-hollow-completion semantics;
                         FINISHED must never claim SUCCESS when verified is false
                         for an artifact-producing phase
git_branch_after
git_head_after
git_signature_after_sha256
changed_paths             target-relative only; absolute paths and ".." rejected
changed_path_count
changed_paths_truncated
stdout_bytes
stdout_sha256
stderr_bytes
stderr_sha256
error_summary_redacted    optional, bounded, sanitized
watchdog_triggered
```

Raw stdout/stderr and changed-file content are never stored; only hashes and
byte counts.

## 6. Append durability and concurrency

A future writer must: open in append mode, take an exclusive process-level
lock around each record append, serialize one complete canonical JSON object,
append exactly one newline, flush, `fsync`, release the lock. The file lock
must not be held during the external invocation itself — only around each
append. The shared `invocation_id` links a STARTED/FINISHED pair; concurrent
appends must not interleave bytes or produce malformed lines.

## 7. Corruption behavior

Readers must not silently skip malformed JSON lines, unknown schema versions,
invalid record types, duplicate incompatible FINISHED records, FINISHED
records without a known STARTED record, invalid invocation IDs, or impossible
lifecycle ordering. On corruption: report the exact line/record identifier,
preserve the file unchanged, do not truncate or auto-repair, block automatic
repeated live driving, require explicit operator resolution.

## 8. Evidence-category separation

The audit log is not readiness evidence, not
`next_feature_execution_evidence.json`, not a proof record
(`docs/*_LIVE_PROOF.md`), not a development receipt, not `DRIVER_OBSERVED`,
not `MANUAL_ATTESTED`, not helper-selection state, not phase-completion state,
not approval state, not source-package truth, and not promotion evidence —
restating the same separation already recorded in
`docs/HLDSPEC_DEVELOPMENT_BACKLOG.md` P1-019 and in
[`TOOLCHAIN_DRIVER_EVIDENCE_CONTRACT.md`](TOOLCHAIN_DRIVER_EVIDENCE_CONTRACT.md)
§6.

No audit-log entry may automatically advance a phase, set readiness, permit
merging, grant execution authority, satisfy a human approval, or convert
manual work into driver-observed work.

## 9. Consumers and five-slice implementation plan

Initial contract consumers are limited to: human/maintainer audit, future
read-only status/doctor diagnostics, and future detection of incomplete
invocation lifecycles. Explicit non-consumers: readiness calculation,
promotion calculation, merge approval, helper selection, source-package
generation, product decisions, provenance classification. **This contract
creates no runtime consumer.**

Each slice below is a separate, separately gated implementation slice.
Nothing beyond this contract doc is authorized by ratifying it; each slice
returns to GATE before it starts.

- **Slice A — path and schema. DONE (2026-07-11).**
  `hldspec/speckit_invocation_audit.py`: canonical pointer-aware path helper,
  closed schema-version-1 STARTED/FINISHED dict validation, deterministic
  serialization. No file writer. No invocation wiring. Tests:
  `tests_v2/test_speckit_invocation_audit.py`.
- **Slice B — durable append writer.** Exclusive append lock, one complete
  NDJSON record per line (§3–§7), flush and `fsync`, corruption detection
  (§7). No `SpecKitInvoker` wiring.
- **Slice C — `SpecKitInvoker` integration.** Append STARTED before external
  invocation and FINISHED after return or termination, per the failure rule
  (§11). Preserves the existing `InvocationResult` shape; exposes audit
  failure separately. `execution_path: "speckit_drive_loop"` is explicitly
  **not** included in this slice.
- **Slice D — drive-loop integration (reserved, not started).** Separate
  `execution_path: "speckit_drive_loop"` coverage and an automatic-continuation
  audit gate for `speckit_drive_loop.py`. Requires its own separate
  authorization and its own separate live proof — not covered by any prior
  single-phase invocation proof.
- **Slice E — read-only diagnostics.** Status/doctor reporting and
  incomplete-lifecycle detection in `hldspec_agent_session.py
  status`/`doctor`. No mutation or repair. No effect on readiness, approval,
  or promotion.

## 10. Retention and privacy

Retention: append-only history retained indefinitely; no automatic deletion,
rotation, compaction, migration, or age-based retention. Any future archive/
rotation/compaction/export/deletion policy requires a separately reviewed
contract preserving invocation identity and audit continuity.

Privacy: never persist prompt text, full stdout/stderr, environment
variables, tokens, credentials, secrets, absolute home-directory paths, or
unrelated user data. Persist only hashes, byte counts, safe identity fields,
target-relative changed paths, and bounded redacted failure summaries.

## 11. Failure rule

Audit durability is mandatory for repeated live execution: failure to write
STARTED blocks invocation; failure to write FINISHED blocks automatic
continuation. Audit failure never fails silently.

## 12. See also

- [`docs/HLDSPEC_DEVELOPMENT_BACKLOG.md`](HLDSPEC_DEVELOPMENT_BACKLOG.md) P1-019 —
  backlog entry this contract resolves; implementation phases (§9) remain open there.
- [`TOOLCHAIN_DRIVER_EVIDENCE_CONTRACT.md`](TOOLCHAIN_DRIVER_EVIDENCE_CONTRACT.md) —
  the `DRIVER_OBSERVED` / `MANUAL_ATTESTED` / readiness-evidence axis this log is
  explicitly distinct from.
- [`TOOLCHAIN_DRIVER_BOUNDARY.md`](TOOLCHAIN_DRIVER_BOUNDARY.md) — ownership zones,
  the anti-hollow-completion gate this log's `verified`/`produced_artifacts` fields
  reuse.
- `hldspec/control_paths.py` — `resolve_hldspec_dir`, the canonical pointer-aware
  resolver this log's path is built from.
- `hldspec/speckit_invoker.py` — `InvocationResult` — the existing fields
  (`returncode`, `ok`, `produced_artifacts`) this log's FINISHED record reuses
  rather than reinventing.
- `hldspec/helper_registry.py` — `helper_id`, `AUTHORITY_EXECUTE_WITH_APPROVAL` —
  existing vocabulary this log's `helper_id`/`authority_level` fields reuse.
- `docs/FIRST_LIVE_E2E_PROOF.md`, `docs/SPECKIT_INVOKER_TASKS_HAIKU_LIVE_PROOF.md` —
  the point-in-time proof records this durable log is explicitly not a replacement
  for producing again by hand.
