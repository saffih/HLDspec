# HLD Completion Architecture Guide

When a source HLD leaves a design detail unspecified, this guide says what
HLDspec may do and what it must stop for.

---

## What may be inferred

HLDspec may proceed with an explicit confidence label when:

- The HLD contains **direct textual evidence** for the conclusion.
- The inference is **reversible** — the spec or plan can be rebuilt if the
  human chooses a different answer.
- The conclusion does **not** affect a human-owned domain (see below).

Label every inference in the output artifact:

```
"evidence_level": "inferred"
"confidence": "MEDIUM"
"source_sections": ["HLD-002", "HLD-007"]
```

---

## What must become an option packet

Generate an `OptionPacket` and add it to `option_packets.json` when the HLD
is silent on any of these human-owned domains:

| Domain | Examples |
|---|---|
| `source_of_truth` | Who owns the authoritative copy of a data entity |
| `api_boundary` | Which service exposes an endpoint; contract ownership |
| `data_ownership` | Who may mutate a field; where it is stored |
| `dependency_order` | Which feature must exist before another |
| `rollout_strategy` | Feature flags, gradual rollout, backward compatibility |
| `security_boundary` | Auth scope, token issuer, permission model |

An option packet includes: decision ID, source HLD sections, missing fact,
options with tradeoffs, recommended default if safe, blast radius, and
whether it affects the constitution.

**The `packet_gate_status()` gate blocks promotion until every packet in these
categories has an accepted answer.**

---

## What must stop for human approval

Stop at a `STOP_CHECKPOINT` when:

- The HLD omits a human-owned decision **and** the decision affects the spec
  build plan, dependency order, or constitution.
- A conflicting answer was given in the decision queue.
- An option packet's `affects_constitution` is `True` — the constitution update
  plan must be reviewed before SpecKit is invoked.
- The prework quality review returns `REWORK_REQUIRED`.

Do not infer. Do not guess. Present the specific decision and wait.

---

## What may affect the constitution

When an option packet is answered and `affects_constitution=True`, HLDspec
must generate a `constitution_update_plan.*` artifact — it must **not** edit
`.specify/memory/constitution.md` directly.

The update plan includes:

```
decision_id:
current_rule: (existing rule text, or "(none)")
proposed_rule:
why:
artifacts_affected:
human_approval_required: true
```

The SpecKit proxy may apply the plan only after explicit human approval.

---

*This guide is intentionally short. For the rationale behind these rules, see
`docs/HLDSPEC_STABILITY_ARCHITECTURE.md` and `docs/ARCHITECTURE_ENHANCEMENT_OPTIONS.md`.*
