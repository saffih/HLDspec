# Flow Journey 2 — Provisional-Section Dependency Register

**Purpose:** Tracks every point where a feature decomposed from the 11
constitution-backed sections references or depends on a provisional section.
Each entry preserves the revisit trigger verbatim.

---

## Register

| # | Feature | Provisional section | Nature of dependency | Revisit trigger |
|---|---|---|---|---|
| 1 | FLOW-F01 | HLD-012 (Technology) | Store implementation uses SQLite + Python 3.10+ — technology choices stated in HLD-012 | assign when the first spec citing this section is drafted — revisit at the next SDD-gate assessment |
| 2 | FLOW-F03 | HLD-012 (Technology) | Runners named (Claude, Devin, Codex) are from HLD-012's confirmed set | assign when the first spec citing this section is drafted — revisit at the next SDD-gate assessment |
| 3 | FLOW-F03 | HLD-002 (Vocabulary) | Verb names (add, next, context, etc.) align with vocabulary in HLD-002 | assign when the first spec citing this section is drafted — revisit at the next SDD-gate assessment |
| 4 | FLOW-F04 | HLD-006 (Escalation triggers) | When a runner escalates is governed by HLD-006 triggers — the fork-join spec defines the mechanism, not the triggers | assign when the first spec citing this section is drafted — revisit at the next SDD-gate assessment |
| 5 | FLOW-F08 | HLD-001 (What it is) | "The report is the point" framing comes from HLD-001 — the output layer spec uses it as motivation but does not derive requirements from it | assign when the first spec citing this section is drafted — revisit at the next SDD-gate assessment |
| 6 | FLOW-F08 | HLD-011 (Scope boundary) | The "separate markdown" rendering of long outcomes is governed by HLD-011's boundary rule (no interface may bypass baton/context integrity) | assign when the first spec citing this section is drafted — revisit at the next SDD-gate assessment |

---

## Resolution Policy

These dependencies are **flagged, not resolved**. Journey 2 does not:
- Invent spec intent for provisional sections.
- Cite provisional sections as requirement anchors.
- Resolve what the provisional section would contain.

When the first spec citing a provisional section is drafted (the revisit
trigger), each dependency above is revisited and either:
- Absorbed (the provisional section's spec confirms the assumed behavior), or
- Flagged for rework (the spec reveals a conflict with the decomposed feature).

---

## Cross-check: No requirement cites a provisional anchor

All 75 requirements in `speckit_single_spec_input.md` cite only anchors from
the 11 decomposable sections. Zero requirements cite HLD-001, HLD-002,
HLD-006, HLD-011, HLD-012, or HLD-017.

---

## HLD-017 Candidate Capabilities — Negative Cross-check

The following HLD-017 candidates are confirmed NOT decomposed, NOT treated as
commitments, and NOT appearing as requirements or spec inputs:

- Web UI — not decomposed
- HTTP API — not decomposed
- Unix sockets — not decomposed
- Daemons — not decomposed
- Worker pools — not decomposed
- Environment staging — not decomposed
- Migration tooling — not decomposed
- Richer UI infrastructure — not decomposed
- React-style reply flows — not decomposed
- Session-log links — not decomposed (the committed-surface version: "links to relevant reports/logs" in HLD-003 projections IS cited, but only from HLD-003 not HLD-017)
- Richer reference surfaces — not decomposed
- Robust markdown/context views — not decomposed

Only the **committed design surface** from HLD-017 feeds decomposition, and
only through its backing sections (HLD-003/004/005/007/008/009/010/013/014/
015/016) which are among the 11 decomposable sections.
