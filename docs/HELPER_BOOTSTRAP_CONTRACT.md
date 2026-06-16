# Helper Bootstrap Contract

**Status:** product/design contract. This defines the **Generic Helper Bootstrap**
— the universal first-contact entrypoint for unknown or newly introduced
tools/skills/harnesses inside Journey 3.

The bootstrap converts a tool/skill instruction into a **candidate HelperContract**
that Journey 3 may eventually operate. It is a gate and a contract generator, not
an executor.

**Core distinction:**

> **Generic Helper Bootstrap** = first-contact intake + candidate contract
> generator. It may reject; it may propose; it does not approve itself.
>
> **Operational Helper** = an approved, bounded helper that guides the targeteer
> through a declared toolchain.
>
> **A candidate helper is not trusted until reviewed and approved by the human.**

Relationship to Journey 3:
`docs/JOURNEY3_HELPER_CONTRACT.md` defines the HelperContract schema that
*operational* helpers fill. This doc defines the **lifecycle** that turns an
unknown tool into such a contract and what a bootstrap may/must not do at each
stage.

---

## 1. Purpose

Helper Bootstrap is the universal first-contact entrypoint for any tool or skill
that a targeteer or maintainer wants to introduce as a Journey 3 helper.

Given a tool/skill instruction (a README, a skill doc, a command reference, or a
URL), Bootstrap:

1. **Inspects** the tool — extracts claims, capabilities, inputs/outputs, known
   limits.
2. **Probes** the tool — checks whether claimed capabilities survive challenge.
3. **Proposes** a candidate HelperContract and a first `NextActionPacket`.
4. **Refuses** if the tool is improper, unsupported, or requires forbidden authority.
5. **Hands off** to human review — it does not approve its own output.

## 2. Non-goals

Bootstrap must not:

- directly operate arbitrary tools or execute commands;
- run SpecKit or any harness;
- modify product code;
- commit, merge, or push;
- become source of truth for capabilities it has not probed;
- invent package fields or target evidence;
- invent tool capabilities not present in the tool instruction;
- approve its own generated candidate helper;
- bypass human approval;
- bypass Journey 1 or Journey 2 gates.

---

## 3. Lifecycle states

States are one-directional except where noted.

```text
UNKNOWN_TOOL
  ↓ (inspection pass)
INSPECTED_TOOL
  ↓ (candidate contract generated)
PROPOSED_HELPER
  ↓ (RunSkeptic + capability probes pass)
REVIEWED_HELPER
  ↓ (human approves)
APPROVED_HELPER
  ↓ (installed/materialized in target)
OPERATIONAL_HELPER

PROPOSED_HELPER → REJECTED_HELPER  (at any probe/review stage)
REVIEWED_HELPER → REJECTED_HELPER  (at human review)
```

| State | Rule |
|---|---|
| `UNKNOWN_TOOL` | Cannot operate. Cannot propose actions. Only records the raw instruction source. |
| `INSPECTED_TOOL` | Has extracted claims/capabilities only. No trust. Claims are provisional. |
| `PROPOSED_HELPER` | Candidate contract only. Not trusted. Default authority `GUIDE_ONLY`. |
| `REVIEWED_HELPER` | Has passed RunSkeptic gate and capability probes. Still not trusted until human approves. |
| `APPROVED_HELPER` | Requires explicit human approval. May be installed/materialized. |
| `REJECTED_HELPER` | Terminal. Must explain why. Source tool may be re-inspected only with new evidence. |
| `OPERATIONAL_HELPER` | The only state allowed to drive the helper loop. Matches `docs/JOURNEY3_HELPER_CONTRACT.md`. |

**Transition guards:**

- `UNKNOWN_TOOL → INSPECTED_TOOL`: tool instruction source is readable and versioned.
- `INSPECTED_TOOL → PROPOSED_HELPER`: all required intake questions (§6) are answered; `cannot_do` and `forbidden_actions` are explicit.
- `PROPOSED_HELPER → REVIEWED_HELPER`: all capability probes (§7) pass; RunSkeptic emits PASS.
- `REVIEWED_HELPER → APPROVED_HELPER`: human explicitly approves.
- `APPROVED_HELPER → OPERATIONAL_HELPER`: helper is installed/materialized in the target under `.hldspec/helpers/<helper_id>/`.
- Any → `REJECTED_HELPER`: a probe fails, RunSkeptic emits CONFLICT, or human rejects.

---

## 4. Authority levels

Bootstrap output is bound to the Journey 3 authority levels
(`docs/JOURNEY3_HELPER_CONTRACT.md §7`):

| Level | Bootstrap rule |
|---|---|
| `GUIDE_ONLY` | **Default for all proposed/candidate helpers.** |
| `PROPOSE_COMMAND` | Allowed for proposed helpers that have passed capability probes. |
| `EXECUTE_WITH_APPROVAL` | **Not allowed for proposed helpers.** Only after APPROVED_HELPER + separate explicit gate. |
| `AUTONOMOUS_WITH_GUARDS` | **Future-only. Refused now at any state.** |

A candidate helper that requests `EXECUTE_WITH_APPROVAL` or higher is
`IMPROPER_USE: UNSUPPORTED_AUTHORITY_REQUEST` and must be rejected.

---

## 5. HelperContract schema

The Bootstrap generates a **candidate** version of the Journey 3 HelperContract.
The schema here is a superset of `JOURNEY3_HELPER_CONTRACT.md §6`: it adds
intake-specific fields that surface during bootstrap and map to the operational
contract on promotion.

Required semantic fields:

| Field | Type | Meaning |
|---|---|---|
| `helper_id` | string | Stable identity slug (e.g. `speckit`, `claude-code`). |
| `display_name` | string | Human-readable name. |
| `toolchain` | string | The harness/tool this helper drives (e.g. `SpecKit`, `Claude Code`). |
| `purpose` | string | One sentence: what task class this helper handles. |
| `status` | enum | Current lifecycle state (§3). |
| `authority_level` | enum | One of the §4 levels. Proposed → `GUIDE_ONLY`. |
| `can_do` | list[string] | Explicit positive capabilities with evidence. |
| `cannot_do` | list[string] | Explicit negative capabilities. Must be non-empty. |
| `required_package_files` | list[string] | `source_package/` files this helper needs. |
| `required_target_evidence` | list[string] | Target repo evidence this helper reads. |
| `required_human_inputs` | list[string] | Decisions/inputs only the human can supply. |
| `allowed_actions` | list[string] | What the helper may recommend/propose. |
| `forbidden_actions` | list[string] | What the helper must never do. Must be non-empty. |
| `questions_to_ask` | list[string] | Questions raised before first action. |
| `stop_rules` | list[string] | Conditions that force a stop. Must be non-empty. |
| `source_files_to_read` | list[string] | Exact files/paths helper cites as evidence. |
| `prompt_template` | string | Template for the helper's next-action prompt. |
| `next_action_format` | string | Expected shape of the next-action output. |
| `report_back_format` | string | Fixed report shape after each step. |
| `completion_criteria` | list[string] | What "done" means for this helper. |
| `sources_used` | list[string] | Tool instruction sources that informed this contract. |
| `known_limits` | list[string] | Honest statement of what this helper cannot or does not cover. |

**Mapping to operational contract:** when a candidate promotes to
`OPERATIONAL_HELPER`, `can_do`/`allowed_actions` map to `recommendable_commands`,
`required_package_files` maps to `required_package_fields`,
`completion_criteria` maps to `final_completion_criteria`. Fields not in the
Journey 3 schema (`display_name`, `purpose`, `sources_used`, etc.) are carried in
`HELPER.md` for human readability.

**Negative capability rule:** `cannot_do`, `forbidden_actions`, `stop_rules`, and
`known_limits` must all be non-empty. A candidate with any of these empty is
`PROPOSED_HELPER` at best; probes will flag it.

---

## 6. Tool/skill intake questions

Applied during `INSPECTED_TOOL → PROPOSED_HELPER` transition. Every question must
be answered or explicitly marked `UNKNOWN` with a human escalation note.

1. What is this tool/skill for? (purpose, task class)
2. What task classes does it support?
3. What inputs are mandatory? What inputs are optional?
4. What outputs does it produce? Which output proves progress?
5. What misuse should it refuse? (negative capability — must be explicit)
6. What state must exist in the target before use?
7. What state must **not** exist before use?
8. What commands/prompts are canonical? (cite the source instruction exactly)
9. What `source_package/` files must be injected as context?
10. What target repo evidence must be inspected before each step?
11. What must be cited as evidence in every next-action prompt?
12. What questions require escalation to the human?
13. What does "done" look like? (completion criteria)
14. What are the known limits the targeteer must be aware of?

A tool that cannot answer questions 5, 7, 11, and 13 cannot proceed past
`INSPECTED_TOOL`.

---

## 7. Capability probes

Checked at `PROPOSED_HELPER → REVIEWED_HELPER`. If probes are not yet
executable, they serve as a **manual review checklist** — each must be marked
PASS/FAIL with evidence or the state remains `PROPOSED_HELPER`.

| Probe | Pass condition |
|---|---|
| **Input declaration** | The contract declares every mandatory input with type and source. |
| **Refusal** | The contract shows one or more concrete examples of tasks it refuses and why. |
| **Source citation** | The contract names exact files/paths it cites — no "read the repo" broad claims. |
| **Bounded next-action** | The contract can produce a prompt with explicit scope, stop rules, and report format — no open-ended "do everything" actions. |
| **No upstream invention** | The contract cannot produce a requirement/feature/boundary unless it cites a package anchor. |
| **Human escalation** | The contract identifies at least one class of decision it must escalate to the human rather than resolve itself. |
| **GUIDE_ONLY operation** | The contract can operate at `GUIDE_ONLY` — reports phase/evidence/next action without executing anything. |

**Failure rules:** any probe FAIL → the candidate stays `PROPOSED_HELPER` (fixable)
or moves to `REJECTED_HELPER` (if the failure is structural and not correctable
without redesign).

---

## 8. Improper-use refusal

First-class refusal statuses. Each refusal must include:
`reason`, `missing_evidence`, `safe_alternative`, `human_question` (if applicable).

| Status | Trigger |
|---|---|
| `IMPROPER_TOOL_FOR_TASK` | The tool's task class does not match the package/target's needs. |
| `INSUFFICIENT_TOOL_CONTRACT` | The tool instruction does not provide enough information to fill the HelperContract schema. |
| `MISSING_PACKAGE_EVIDENCE` | Required `source_package/` files are absent; the package may not have PASSed Journey 2. |
| `MISSING_TARGET_EVIDENCE` | Required target repo evidence is absent and not obtainable without Journey 2 completion. |
| `HUMAN_DECISION_REQUIRED` | A capability claim requires a human-owned architecture/scope/source-of-truth decision. |
| `UPSTREAM_GATE_NOT_PASS` | Journey 1 or Journey 2 did not PASS; bootstrap cannot operate on an unqualified package. |
| `UNSUPPORTED_AUTHORITY_REQUEST` | The tool requests or requires `EXECUTE_WITH_APPROVAL` or `AUTONOMOUS_WITH_GUARDS` for a proposed helper. |

Refusals are recorded in `.hldspec/helpers/proposed/<helper_id>/REJECTED.json`
(future layout — see §10).

---

## 9. NextActionPacket

The primary target-facing output of Bootstrap (and of any operational helper per
step). The targeteer should always know: what to do now, with what tool, using
what prompt, what sources justify it, what is missing, when to stop, what to
report back.

Required fields:

| Field | Meaning |
|---|---|
| `current_state` | The lifecycle state this packet is produced from (§3). |
| `proposed_or_selected_helper` | The `helper_id` this packet references. |
| `tool_to_use` | The exact tool/harness/command surface. |
| `exact_prompt_or_command` | The baked, cite-sourced prompt or command. Never open-ended. |
| `files_to_inject` | Exact `source_package/` or target files to include as context. |
| `sources_used` | What package/target evidence justifies this action. |
| `missing_questions` | Questions that must be answered before the prompt may be sent. |
| `stop_rules` | Conditions under which the targeteer must stop and not continue. |
| `do_not_run_yet` | Actions that must not be taken until a stated precondition is met. |
| `expected_output` | What a successful run produces (proof of progress). |
| `report_back_format` | Exact fields the targeteer must report after the step. |
| `confidence_level` | `HIGH` (probed + approved), `MEDIUM` (inspected, unprobed), `LOW` (proposed only). |
| `known_limits` | Honest statement of what this packet cannot cover. |

**Rules:**
- `missing_questions` non-empty → do not send `exact_prompt_or_command` yet.
- `confidence_level: LOW` → the packet is advisory only; human reviews before action.
- `stop_rules` must always be non-empty.
- `sources_used` must cite real files/anchors; broad "read the codebase" claims fail the probe.

---

## 10. Target-local layout (future direction)

Define the eventual on-disk layout without implementing it now.

```text
.hldspec/
  helpers/
    README.md                          ← index of installed helpers
    BOOTSTRAP.md                       ← this contract, pinned version
    registry.json                      ← {helper_id: status, ...}
    speckit/                           ← the one operational helper today
      HELPER.md
      helper_contract.json
    proposed/
      <helper_id>/
        candidate_HELPER.md
        candidate_helper_contract.json
        first_next_action_packet.md
        REJECTED.json                  ← written on rejection

  next_action/                         ← current active next-action packet
    action.md
    prompt.md
    sources.md
    questions.md
    stop_rules.md
    report_back.md

  helper_selection.json                ← Journey 3 selected helper state

source_package/
  helper_recommendations.json          ← Journey 2 advisory output (implemented)
```

Storage ownership (unchanged from P1-012 design note):

| File | Owner | Contents |
|---|---|---|
| `source_package/helper_recommendations.json` | Journey 2 | Advisory recommendations — what helpers fit this package. |
| `.hldspec/helper_selection.json` | Journey 3 | Selected helper state — which helper was chosen. |
| `.hldspec/helpers/<id>/helper_contract.json` | Bootstrap → Journey 3 | Operational contract for the installed helper. |
| `.hldspec/runtime/MANIFEST.json` | Runtime installer | Runtime provenance only — version, source commit, vendor manifest. |

---

## 11. Gate states — PASS / ACTION / BLOCKED

| State | Meaning | Trigger |
|---|---|---|
| **PASS** | Tool is inspected, probes pass, candidate contract is complete with explicit negative capabilities, first NextActionPacket can be produced, no unsupported authority requested, human can safely approve or reject. | All intake questions answered, all probes PASS, `cannot_do`/`forbidden_actions`/`stop_rules`/`known_limits` non-empty, authority ≤ `PROPOSE_COMMAND`, `confidence_level` at least `MEDIUM`. |
| **ACTION** | Tool is probably usable but something is missing or incomplete; fixable without design change. | Intake questions partially answered, one or more probes inconclusive (not FAIL), package evidence missing but obtainable from a PASSed Journey 2 package, human must answer bounded questions. |
| **BLOCKED** | Bootstrap cannot produce a safe candidate. | Tool is improper for the task; tool requires unsupported authority; tool cannot cite sources; tool would need to invent upstream truth; Journey 2 package did not PASS; candidate cannot define stop rules; an unresolved product/architecture decision is required. |

---

## 12. RunSkeptic

**Source read:** `/Users/saffi/code/skeptic/skeptic.md` (read in this session).
**Permission mode:** read-only on this contract.

Applied to the Helper Bootstrap contract design:

**CH (inversion — what bad outcome if bootstrap trusts arbitrary tool claims):**
A tool claiming "I can implement the full feature from one prompt" would be
`INSPECTED_TOOL` and generate an overconfident candidate. Without negative
capability enforcement and capability probes, it could reach `OPERATIONAL_HELPER`
and execute open-ended work with no stop rules. Bounded by: (1) `cannot_do` and
`stop_rules` must be non-empty at `PROPOSED_HELPER`; (2) the "no upstream
invention" probe explicitly challenges broad capability claims; (3) `AUTONOMOUS_WITH_GUARDS`
is refused; (4) human approval is required before `OPERATIONAL_HELPER`.
**PASS.**

**OM (parsimony — too much process?):**
The lifecycle has 7 states. Each prevents a specific failure: `UNKNOWN` can't
operate (prevents use before inspection); `INSPECTED` has no trust (prevents
acting on unverified claims); `PROPOSED` can't self-approve (prevents trust
inflation); `REVIEWED` requires probes (prevents unverified capability claims);
`APPROVED` requires human (prevents silent enablement); `REJECTED` is terminal
(prevents retry without new evidence). Removing any state collapses two failure
modes into one undetected path. `OM:SS` check: the `NextActionPacket` and
HelperContract schema do have more fields than the minimal Journey 3 HelperContract
— justifiable because bootstrap is the intake function; the superset maps down to
the operational contract on promotion, not duplicate. **PASS** with a note:
`sources_used` appears in both `NextActionPacket` and `HelperContract` — keep
the single source; don't replicate per packet unless it differs from the contract.

**FE (mechanism — clear enough to execute later?):**
Intake questions (§6) produce the raw data. Probes (§7) challenge the data.
Lifecycle transitions (§3) have explicit guards. Each refusal status (§8) has
`reason/missing_evidence/safe_alternative/human_question` — a reader can execute
this as a checklist today. The target-local layout (§10) shows exactly where
outputs land. `FE:ME` gap: §7 probe "no upstream invention" is stated as a
property to check but does not specify *how* to check it mechanically in future
automation — that is acceptable for a design contract, but the eventual code
must make it executable. **PASS** with the mechanical-check gap logged in §14.

**PO (refutation — can a bad/improper tool be rejected?):**
Improper-use refusal statuses (§8) are first-class; `IMPROPER_TOOL_FOR_TASK`
must be emitted when the task class doesn't match. Capability probes have
explicit FAIL conditions. `cannot_do` and `forbidden_actions` being empty is a
probe failure. `PO:CO` check: are there disconfirming paths? Yes — a tool that
passes all probes but fails human review → `REJECTED_HELPER`. A tool that fails
even one structural probe → `REJECTED_HELPER`. The `BLOCKED` gate prevents a
candidate from reaching PASS silently. **PASS.**

**KT (universalizability — safe if every future helper uses it?):**
Each helper fills the same HelperContract schema. Authority caps are the same for
all proposed helpers. No special-pleading for specific helper types. A speckit-only
shortcut is not carved out. **PASS.**

**SH (tradeoff — generic extensibility vs bounded human-controlled operation):**
Dominant side: bounded human-controlled operation (default `GUIDE_ONLY`, human
approval required, self-approval forbidden). Narrow exception: a probed+approved
helper may reach `PROPOSE_COMMAND` and eventually `EXECUTE_WITH_APPROVAL` after a
separately gated step — but not as part of bootstrap. `SH:FM` check: is there a
fake middle where "generic enough to accept anything" and "bounded enough to be
safe" coexist? No — the refusal statuses and the probe requirements mean the gate
genuinely blocks improper tools. **PASS.**

Verdict: **HANDLED.** The §14 known-limit (mechanical "no upstream invention"
probe) is logged as a design-to-implementation gap, not a blocker.

---

## 13. Validation strategy

**Automated (existing seams):**
Doc-contract tests (`tests_v2/test_hldspec_concept_docs.py`,
`test_terminology_and_flow_docs.py`) enforce the docs index and canonical
terminology. The new doc must appear in `DOCS_INDEX.md` (§13 below) and must
not contradict `JOURNEY3_HELPER_CONTRACT.md`'s existing authority level and
HelperContract field definitions.

**Manual checklist:**
1. Every lifecycle state has at least one explicit guard for entry and one for exit.
2. Every refusal status has all four required sub-fields
   (reason, missing_evidence, safe_alternative, human_question).
3. Every probe has a binary PASS/FAIL condition.
4. `cannot_do`, `forbidden_actions`, `stop_rules`, `known_limits` are all
   required — a candidate with any empty fails probes.
5. No lifecycle state allows `EXECUTE_WITH_APPROVAL` or higher before
   `APPROVED_HELPER`.
6. The storage table (§10) matches the P1-012 design note in the backlog.

---

## 14. Known limits (honest scope)

- **Not implemented.** No code generates `.hldspec/helpers/` files, a registry,
  or `NextActionPacket` artifacts. The layout (§10) is the intended direction;
  these are implementation slices for future gated work.
- **"No upstream invention" probe is manual today.** Mechanically checking that a
  candidate contract cannot cite invented anchors requires integration with
  `hld_source_package.py`'s anchor map — deferred to the first bootstrap runtime
  slice.
- **Single helper exists.** The `speckit` helper is `OPERATIONAL_HELPER` by
  existing implementation; it did not go through this bootstrap process (it
  predates the contract). Retrofitting it into a formal `registry.json` entry is
  a maintenance task, not a blocker.
- **`NextActionPacket` is a schema contract only.** No writer or renderer exists.
  The speckit run-card (`next_feature_readiness`) is its de facto realization for
  `helper: speckit`; formalizing the alignment is a future slice.
