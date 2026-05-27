"""Canonical handoff policy blocks shared by generated prompts and Run Cards.

Generated bundle prompts and SpecKit Run Cards are first-class executable
handoff contracts. The operational policy a receiving agent must follow —
one-go execution, answer-finding, the HLD section gap map, clarification rules,
how to run RunSkeptic, and how to file a reassessment request — must be
identical everywhere it appears. This module is the single source for that
text so the two renderers cannot drift.

Each function returns a list of markdown lines beginning with its `##` heading
so callers can splice it in once.
"""

from __future__ import annotations


def one_go_execution_policy_block() -> list[str]:
    return [
        "## One-Go Execution Policy",
        "",
        "Do as much as safely possible in one run.",
        "Clarification is not a stop by default.",
        "Do not stop just because SpecKit asks a question.",
        "Resolve clarification questions from approved evidence first, then continue when the answer is evidence-backed.",
        "Stop only at a real blocker: approved evidence is missing, approved evidence is contradictory, the question requires a human-owned decision, RunSkeptic returns ACTION or CONFLICT, a test or validation fails, implementation would begin without approval, or scope expands beyond the approved package/group.",
        "On a real blocker, emit the structured reassessment request below instead of guessing or silently halting.",
        "",
    ]


def answer_finding_protocol_block() -> list[str]:
    return [
        "## Answer-Finding Protocol",
        "",
        "Before escalating any clarification, resolve them from approved evidence first using this order:",
        "",
        "1. active HLD sections and the Working HLD",
        "2. the HLD Section Gap Map below",
        "3. role reviews (architecture, product, governance) and the role review summary",
        "4. the spec package map",
        "5. the feature dependency graph",
        "6. the SpecKit invocation queue",
        "7. the constitution update plan or approved constitution and the prework quality review",
        "8. the Run Card and the SpecKit proxy dossier",
        "",
        "Continue when the answer is directly supported by approved evidence.",
        "Escalate only when approved evidence is missing, approved evidence is contradictory, or the question requires a human-owned decision.",
        "",
    ]


def hld_section_gap_map_block() -> list[str]:
    return [
        "## HLD Section Gap Map",
        "",
        "Map each clarification to the evidence dimension it belongs to, then read the matching approved evidence before escalating:",
        "",
        "- Feature purpose -> active HLD sections, spec package map, product review",
        "- Architecture boundary -> architecture review, dependency graph, proxy dossier",
        "- Source of truth -> architecture review, constitution, data-ownership evidence",
        "- Dependency order -> feature dependency graph, invocation queue",
        "- Acceptance and scope -> active HLD sections, product review, package map",
        "- Governance and approval -> governance review, constitution update plan, prework approval",
        "",
        "If the mapped evidence answers the question, continue. If it is missing or contradictory, stop and escalate.",
        "",
    ]


def clarification_policy_block() -> list[str]:
    return [
        "## Clarification Policy",
        "",
        "Clarification questions are not blockers by default.",
        "",
        "- First answer from approved HLDspec evidence: active HLD sections, Working HLD, spec package map, dependency graph, invocation queue, constitution update plan or approved constitution, role reviews, Run Card, and proxy dossier.",
        "- If approved evidence clearly answers the question, answer it and continue.",
        "- If a pre-approved default is safe and reversible and does not affect architecture, source of truth, security/privacy, data ownership, dependency order, feature scope, constitution rules, user-visible behavior, or implementation approval, answer it and continue.",
        "Stop only when approved evidence is missing, approved evidence is contradictory, or the question requires a human-owned decision.",
        "- Escalate to the human only when approved evidence is missing, contradictory, or the answer is human-owned.",
        "- Stop on RunSkeptic ACTION or CONFLICT.",
        "",
    ]


def runskeptic_operating_block(skeptic_path: str = "~/code/skeptic/skeptic.md") -> list[str]:
    return [
        "## How to run RunSkeptic",
        "",
        "RunSkeptic is the required quality gate for this step.",
        "",
        "First, read the actual current framework file:",
        "",
        f"`{skeptic_path}`",
        "",
        "Do not rely on memory or a summary if the file is available.",
        "",
        "Apply this flow in order:",
        "",
        "`GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN`",
        "",
        "RunSkeptic is normally read-only unless this handoff explicitly authorizes a fix.",
        "",
        "Use only these result statuses:",
        "",
        "- `PASS`: no blocking finding is known; evidence is sufficient for this step.",
        "- `ACTION`: a fixable issue exists, such as missing evidence, stale artifact, invalid output, incomplete contract, weak testability, or unclear prompt/report content.",
        "- `CONFLICT`: a human-owned or architecture/product/source-of-truth decision is unresolved, or multiple valid designs exist and the evidence does not choose between them.",
        "",
        "Minimum checks:",
        "",
        "1. Gate: confirm the requested step is clear, bounded, and testable.",
        "2. Fundamental scan: check purpose, boundaries, ownership, source of truth, main flow, interfaces, dependencies, and high-risk assumptions.",
        "3. Map: list findings before deciding. Do not fix while mapping.",
        "4. Confidence: identify unknowns, skipped areas, and weak evidence.",
        "5. Stabilize: merge related findings and identify root cause.",
        "6. Evidence: mark each finding as `OBSERVED`, `REPRODUCED`, `HISTORICAL`, or `INFERRED RISK`.",
        "7. Decide: choose `PASS`, `ACTION`, or `CONFLICT`; do not promote if any ACTION or CONFLICT remains.",
        "8. Verify: if a fix was explicitly authorized, report the exact tests or checks run; otherwise report what verification would be required.",
        "",
        "Required RunSkeptic output:",
        "",
        "- `RunSkeptic status: PASS | ACTION | CONFLICT`",
        "- `Scope reviewed:`",
        "- `Evidence used:`",
        "- `Findings:`",
        "- `Unknowns:`",
        "- `Human decisions needed:`",
        "- `Verification performed:`",
        "- `Next safe action:`",
        "",
        "Stop immediately if RunSkeptic returns ACTION or CONFLICT, required evidence is missing, a human-owned decision appears, or the step would require reading outside approved evidence.",
        "",
        "If the framework file is unavailable, do not claim full RunSkeptic compliance. Use this embedded fallback and report: `RunSkeptic source: embedded fallback`; `Confidence: lower than full framework review`; `Missing evidence: actual skeptic.md was unavailable`.",
        "",
    ]


def reassessment_request_block() -> list[str]:
    return [
        "## Reassessment Request",
        "",
        "When a real blocker stops the run, do not guess and do not silently halt. Return this structured reassessment request to HLDspec:",
        "",
        "```text",
        "Reassessment request",
        "Blocker type: <missing evidence | contradictory evidence | human-owned decision | RunSkeptic ACTION | RunSkeptic CONFLICT | test failure | scope expansion | implementation approval missing>",
        "Active package:",
        "Phase reached:",
        "What was completed:",
        "What is blocked:",
        "Evidence consulted:",
        "Why approved evidence is insufficient:",
        "RunSkeptic status:",
        "Options considered:",
        "Recommended next safe action:",
        "```",
        "",
        "File this request only for a real blocker: approved evidence is missing, approved evidence is contradictory, a human-owned decision is required, RunSkeptic returns ACTION or CONFLICT, a test or validation fails, scope expands beyond the approved package, or implementation approval is missing.",
        "",
    ]
