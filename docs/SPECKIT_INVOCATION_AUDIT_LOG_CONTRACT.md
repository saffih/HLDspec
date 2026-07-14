# SpecKit Invocation Audit Log Contract

**Status: RATIFIED DESIGN CONTRACT. Runtime implementation: Slices A–B
IMPLEMENTED, C–E NOT IMPLEMENTED. Runtime invocation integration: NOT
IMPLEMENTED.**
The design questions below are resolved; Slice A (path helper + schema
validator) and Slice B (durable append writer), both in
`hldspec/speckit_invocation_audit.py`, are implemented — no code in this repo
implements the reader or CLI surfaces described below, and no production
invocation path calls the writer. This doc resolves the open design
questions recorded in
[`docs/HLDSPEC_DEVELOPMENT_BACKLOG.md`](HLDSPEC_DEVELOPMENT_BACKLOG.md) P1-019
and records a five-slice implementation plan (§9). Ratifying this contract
authorized no implementation slice by itself: the writer, runtime
integration, reader, CLI output, and `speckit_drive_loop.py` wiring each
still require their own separate gate before work starts.

**Slice C decision ratification (2026-07-14, §12):** the three consequential
design decisions that previously blocked Slice C implementation-readiness —
audit-failure exposure mechanism, no-explicit-model representation, and
pre-execution signature-failure handling — are ratified in §12. Slice C is
now design-ready but remains **NOT IMPLEMENTED**; ratifying these decisions
authorizes no code change and does not itself start Slice C — Slice C still
requires its own separate gated implementation task.

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
model                  routed model identity; null when routing is disabled
                       (`route_models=False`) — see §12.2
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

Failure to obtain `git_signature_before_sha256` blocks STARTED construction —
see §12.3.

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

Failure to obtain `git_signature_after_sha256` after the external command has
already run is a FINISHED-construction failure, distinct from a
pre-execution (STARTED-side) signature failure because the command has
already executed and blocking is no longer possible — see §12.1 and §12.3.

## 6. Append durability and concurrency

The implemented Slice B writer (`append_invocation_record`) opens the audit
file in append mode, takes an exclusive process-level lock around each
record append, serializes and appends one complete canonical JSON object
plus one newline, performs the required file and parent-directory `fsync`
sequence, and releases the lock. The implementation writes via unbuffered
`os.write` calls on a raw file descriptor, so there is no separate
userspace-buffer `flush()` step; `fsync` is the durability barrier and is
performed after the complete line has been written. The file lock is not
held during the external invocation itself — only around each append. The
shared `invocation_id` links a STARTED/FINISHED pair; concurrent appends
cannot interleave bytes or produce malformed lines.

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
- **Slice B — durable append writer. DONE (2026-07-11).**
  `hldspec/speckit_invocation_audit.py:append_invocation_record`. Tests:
  `tests_v2/test_speckit_invocation_audit_writer.py`.
  - Accepts a caller-supplied, already-validated record; performs no record
    construction of its own.
  - Resolves the canonical path via the same pointer-aware
    `resolve_invocation_audit_log_path` Slice A defined — normal and
    external-controller mode both covered.
  - A single exclusive `flock` on the audit file covers the entire
    operation: scanning and validating existing history, validating the new
    record's lifecycle transition against that history, appending the line,
    and the full durability sequence below — released on every exit path,
    including every failure.
  - Existing corruption (malformed JSON, non-object lines, schema-invalid
    records, duplicate/incompatible STARTED-FINISHED pairs, a trailing line
    with no final newline) is rejected via `InvocationAuditCorruptionError`
    without modifying the file.
  - A successful append performs, in order and unconditionally (regardless
    of which process, if any, created each path component): `fsync` the
    audit file, then `fsync` the audit directory, the `.hldspec` directory,
    and the resolved root directory — so a writer that finds every component
    already present still gets independent durability proof for the whole
    chain, not just for its own writes.
  - The resolved audit root is opened by walking every real directory
    component of it — not by a single `O_NOFOLLOW` open of the assembled
    path — from a fixed anchor (`/` for an absolute root, `.` for a relative
    one), opening each component with `O_NOFOLLOW`. A one-shot open only
    protects the trailing path component the kernel resolves; every
    ancestor component is resolved by the kernel's normal lookup, and an
    attacker-controlled symlink anywhere in that ancestry would otherwise be
    followed silently. The component walk closes each intermediate fd as it
    advances and returns exactly one open fd for the resolved root itself,
    used for the `.hldspec`/audit/file creation and `fsync` steps already
    described above. Every symlink in the traversal is rejected — including
    a symlinked `.hldspec` directory, audit directory, or audit file, as
    before — with exactly one narrow exception:
    - **Trusted Darwin root aliases.** Stock macOS ships `/var` and `/tmp` as
      root-owned symlinks to `private/var` and `private/tmp`; rejecting them
      outright would break most real macOS target paths, since `/tmp`,
      `TMPDIR`, and `/var/folders/...` are all spelled through these
      aliases by the platform itself. When, and only when, all of the
      following hold, the writer substitutes the real `private/var` or
      `private/tmp` components (themselves opened with `O_NOFOLLOW` like
      every other component) instead of following the alias:
      - the platform is Darwin;
      - the alias is the *first* component of an *absolute* resolved root
        (never a relative root, never a later component);
      - the anchor `/` directory is owned by UID 0 and is not
        group- or world-writable;
      - the alias entry itself is a symlink owned by UID 0;
      - its `readlink` target is exactly `private/var`/`/private/var` (for
        `var`) or `private/tmp`/`/private/tmp` (for `tmp`) — no prefix,
        suffix, or nested variation is accepted.
      No other alias — `/etc`, any other root-level symlink (including other
      stock Darwin symlinks such as `/home`), a nested alias, a
      dynamically-discovered alias, or any alias on a non-Darwin platform —
      is authorized. This exception does not use `Path.resolve()`,
      `os.path.realpath()`, or any other generic canonicalization; it is two
      exact, explicitly authorized substitutions and nothing else.
    - **Disclosed limits.** A relative resolved root's traversal starts from
      the process's already-open current working directory; the historical
      path used to reach that working directory is not itself revalidated.
      This hardening is self-contained to the audit writer's own root
      traversal and does not change `control_paths`/`run_state` pointer
      resolution — the pointer that selects the normal or external-controller
      root is read exactly as before this hardening. The Darwin alias trust
      checks assume the standard, unmodified stock configuration
      (root-owned `/`, root-owned alias symlinks); a privileged attacker able
      to replace those root-owned filesystem objects, replace a mount
      namespace, or otherwise act as root is outside this threat model, the
      same as for every other root-owned path this writer already trusts.
  - The history scan reads in bounded chunks, so multi-line history is
    processed incrementally and the entire log is not normally loaded into
    memory at once; the current line is still buffered in full until its
    terminating newline, so one extremely large or unterminated line can
    consume memory proportional to that line's length. Lifecycle validation
    also keeps state keyed by every `invocation_id` for the duration of the
    scan — the STARTED/FINISHED information needed to detect duplicates,
    orphans, incompatible pairs, and ordering violations — so total memory
    grows with both the largest current line and the number/size of
    lifecycle entries. No total record-size limit or bounded-total-memory
    guarantee is currently ratified.
  - No runtime code constructs or submits records through this writer, no
    production invocation path calls it, and no audit record is emitted
    automatically by anything in this repo today.
  - No public reader or diagnostics exist yet (Slice E).
  - `SpecKitInvoker`/`speckit_drive_loop.py` wiring (Slice C/D) requires its
    own separate authorization and is explicitly not part of this slice.
- **Slice C — `SpecKitInvoker` integration. Design-ready (decisions ratified
  2026-07-14, §12); NOT IMPLEMENTED.** Append STARTED before external
  invocation and FINISHED after return or termination, per the failure rule
  (§11) and the ratified failure/identity decisions (§12). Preserves the
  existing `InvocationResult` shape; exposes audit failure separately via the
  mechanism in §12.1. `execution_path: "speckit_drive_loop"` is explicitly
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
continuation. Audit failure never fails silently. Failure to obtain the
pre-execution Git signature is a STARTED-construction failure and is governed
by this same rule — see §12.3.

## 12. Slice C failure and identity decisions (ratified 2026-07-14)

This section ratifies the three consequential design decisions that
previously blocked Slice C implementation-readiness. Ratifying these
decisions is a **documentation-only act**: it authorizes no code, no test,
and no schema-validator change, and does not itself start Slice C. Slice C
remains **NOT IMPLEMENTED**. Where a rule below states target behavior that
the current Slice A/B validator (`hldspec/speckit_invocation_audit.py`) does
not yet implement (e.g. a `model: null` path, an audit-failure exception
type), that is explicitly a **deferred Slice C implementation requirement**,
not a description of current validator behavior — the current validator
requires non-empty `model` and hex64 `git_signature_before_sha256`/
`git_signature_after_sha256` with no null path, and continues to do so until
Slice C's own implementation task amends it.

### 12.1 Audit-failure exposure (STARTED and FINISHED)

MUST: on STARTED-write failure (including STARTED-record construction
failure — e.g. an unavailable pre-execution signature, §12.3), the external
command MUST NOT run, and the caller MUST receive a dedicated audit-failure
signal.

MUST: on FINISHED-write failure (including FINISHED-record construction
failure — e.g. an unavailable post-execution signature) after the external
command has already executed, the true command outcome MUST NOT be
discarded, replaced, or falsely converted to success; the caller MUST
receive a dedicated audit-failure signal separately from the real result;
automatic continuation MUST be blocked; and the unmatched `STARTED` record
stands as durable evidence of an incomplete lifecycle, per §4.

MECHANISM: the audit-failure signal MUST be a dedicated exception type that
extends the existing `InvocationAuditError` hierarchy
(`hldspec/speckit_invocation_audit.py:613`) — this ratifies that Slice C's
implementation will extend that hierarchy; it does not itself define any
class. The exception MUST NOT carry the full `InvocationResult` (which holds
raw `stdout`/`stderr`) as a directly-inspectable attribute. Instead:
- the exception MUST carry, at minimum, `invocation_id`, `phase`, and
  `skill` — so an operator can correlate the failure with a specific
  attempt — and MAY additionally carry other bounded, already-sanitized
  fields (e.g. `returncode`, hashes, byte counts — values that are already
  safe to persist per §5.3/§10);
- a separate, explicitly documented mechanism MUST exist for a caller to
  retrieve the real `InvocationResult` after a FINISHED-write failure (the
  exact shape — accessor method, injected sink, or documented
  catch-and-read pattern — is Slice C implementation latitude, not a policy
  question this contract leaves open).

PUBLIC CALL SHAPE: `invoke()` continues to return a plain `InvocationResult`
on the non-audit-failure path; it raises the dedicated audit-failure
exception on STARTED or FINISHED audit failure. No wrapper/envelope return
type is introduced. `InvocationResult`'s dataclass shape
(`hldspec/speckit_invoker.py:71-90`) remains byte-for-byte unchanged.

STARTED FAILURE OBSERVABLE: via the raised exception, before the external
command runs.

FINISHED FAILURE OBSERVABLE: via the raised exception, after the external
command has already run.

ACTUAL INVOCATION RESULT LOCATION: for FINISHED failure, retrievable via the
separately documented retrieval mechanism above — never embedded directly
and unboundedly in the exception.

CALLER OBLIGATION: callers of `invoke()` (currently
`hldspec/machines/speckit_execution.py:221,308` and
`scripts/proof_e2e_v0.py:451,455`) MUST NOT wrap the call in a broad
`except Exception` (or any handler) that silently swallows the
audit-failure exception. A caller MAY catch the specific audit-failure
exception type to surface it to a human/operator, but MUST NOT
automatically retry or continue as if the invocation were unaudited.

AUTOMATIC CONTINUATION RULE: MUST NOT auto-continue or auto-retry after any
audit-failure exception, per §11.

PRIVACY / REDACTION RULE: the audit-failure exception's `__str__`,
`__repr__`, and any structured-logging representation MUST be limited to the
bounded sanitized fields listed above. Raw prompt text, full `stdout`, and
full `stderr` MUST NOT appear on the exception's default string, repr, or
logging surface, matching the existing `InvocationAuditError` docstring rule
("never include complete raw record content in `message` or these fields").
This rule governs the exception's own representation only. The real
`InvocationResult`, once retrieved via the separate documented mechanism
above, is the same pre-existing dataclass callers already receive on the
non-audit-failure path (`hldspec/speckit_invoker.py:71-90`) and already
carries raw `stdout`/`stderr` today — this contract does not newly restrict
what a caller does with an `InvocationResult` it already legitimately holds;
it restricts only what the audit-failure exception itself exposes by
default.

BACKWARD-COMPATIBILITY EFFECT: `InvocationResult`'s shape is unchanged.
Existing tests in `tests_v2/test_speckit_invoker.py` that construct
`SpecKitInvoker` without any audit wiring and expect a plain
`InvocationResult` return MUST continue to pass unmodified — Slice C's
implementation MUST NOT make audit writing unconditional in a way that
breaks those fixtures (following the existing `runner`/`change_detector`
injection precedent, `hldspec/speckit_invoker.py:110-117`).

### 12.2 No explicit `--model` flag (`route_models=False`)

MODEL FIELD DOMAIN: `model` MAY be schema-`null`. `model` records what was
*requested* of `SpecKitInvoker` (via `phase_models`/`route_models`); it MUST
NOT assert a concrete effective model identity that the external `claude`
runtime was not told to use. This is a deferred validator amendment — the
shipped Slice A/B validator currently requires non-empty `model` on every
record (`hldspec/speckit_invocation_audit.py:410-412`) and has no null path
yet.

NO-FLAG REPRESENTATION: when `model` is `null`, `argv_without_prompt` MUST
contain zero `--model` occurrences. When `model` is a non-empty string,
`argv_without_prompt` MUST contain exactly one `--model` occurrence whose
value equals `model` (existing rule, unchanged).

ARGV VALIDATION RULE: the deferred validator amendment MUST enforce the
symmetric rule above — not merely permit zero occurrences when `model` is
null, but require exactly zero in that case, so a `null` model can never
coexist with a fabricated `--model` flag.

ROUTE_MODELS_FALSE BEHAVIOR: `SpecKitInvoker(route_models=False)` is a
supported, currently-exercised production configuration
(`scripts/proof_e2e_v0.py:451`). It MUST continue to produce a command with
no `--model` flag and, once Slice C is implemented, an audit record with
`model: null`. This decision requires no change to
`scripts/proof_e2e_v0.py` or any other production caller.

PROOF_E2E_V0 COMPATIBILITY: `scripts/proof_e2e_v0.py`'s default
(`route_models=False`) path becomes schema-compliant under the deferred
validator amendment without any production-code change.

REPRODUCIBILITY LIMITATION: no field in this schema can assert which model
the external `claude --print` process actually selected when invoked
without `--model` — that runtime's own default-model behavior is opaque to
`hldspec/command_runner.py` (a bare `subprocess.run` wrapper) and is out of
scope for this contract to observe or claim.

### 12.3 Pre-execution (and post-execution) Git-signature failure

PREFLIGHT FAILURE BEHAVIOR: fail closed. Inability to obtain the
pre-execution Git signature (`SpecKitInvoker._safe_signature()` returning
`None` before the external command runs) is a STARTED-construction failure
and is governed by §12.1's STARTED-failure rule. No null or sentinel value
for `git_signature_before_sha256` is authorized; the field's existing
hex64-only requirement (`hldspec/speckit_invocation_audit.py:443-446`) is
unchanged.

EXTERNAL COMMAND RUNS: no.

STARTED RECORD WRITTEN: no — STARTED cannot be validly constructed without a
real signature, so none is written, and none is fabricated.

BINDING STATUS: not applicable to this failure — `target_binding.binding_status`
(§5.2) is a distinct field governing target-resolution confidence, not
pre-execution signature availability. This decision does not extend or
repurpose `binding_status` for signature-collection failure.

OPERATOR-VISIBLE FAILURE: yes, via the same audit-failure exception
mechanism as §12.1's STARTED-failure path — no separate mechanism is
introduced.

AUTOMATIC CONTINUATION: MUST NOT auto-continue or auto-retry after a
preflight signature failure, per §11.

Symmetric post-execution case: failure to obtain the post-execution Git
signature (`git_signature_after_sha256`) occurs after the external command
has already run, so blocking the invocation is no longer possible. This is
governed as a FINISHED-construction failure under §12.1's FINISHED-failure
rule, not as a STARTED-style block: the real `InvocationResult` (which
already exists at that point) MUST be preserved and retrievable per §12.1,
automatic continuation MUST be blocked, and the unmatched `STARTED` record
stands as durable evidence of an incomplete lifecycle. No null or sentinel
value for `git_signature_after_sha256` is authorized; a best-effort FINISHED
record using a fabricated or missing after-signature is explicitly
prohibited, since it would make `produced_artifacts`
(`before != after`, `hldspec/speckit_invoker.py:160`) misrepresent an
artifact-producing run.

### 12.4 Unchanged boundaries

Nothing in this section expands Slice C's scope, authorizes Slice D
(`speckit_drive_loop.py`, §9) or Slice E (read-only diagnostics, §9), or
changes the evidence-category separation in §8. The audit log created by a
future Slice C implementation remains not readiness evidence, not approval
evidence, not promotion evidence, and creates no runtime consumer, exactly
as ratified in §8/§9.

## 13. See also

- [`docs/HLDSPEC_DEVELOPMENT_BACKLOG.md`](HLDSPEC_DEVELOPMENT_BACKLOG.md) P1-019 —
  backlog entry this contract resolves; Slices A–B are implemented, Slice C is
  design-ready (§12) but not implemented, Slices D–E remain open.
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
