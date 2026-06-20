#!/usr/bin/env python3
"""Non-stateful SpecKit skill evidence probe (read-only, mutates nothing, runs nothing).

This is the *non-stateful counterpart* to scripts/proof_speckit_readiness.py. That
doctor invokes a live ``claude --print /speckit-* ...`` smoke to test skill
availability (stateful: it spawns an agent and, as proof_e2e_v0.py documents, the
workflow skill can even dirty the target). This probe answers the same question --
"does this target carry the on-disk evidence needed to run ``/speckit-*``?" -- by
reading the filesystem only. It never spawns ``claude``, never runs SpecKit init,
and never writes into the target.

Two independent on-disk signals (both materialized by a real
``specify init . --integration claude`` -- see proof_e2e_v0.py):
  1. ``.specify/``                              -- SpecKit workflow scaffolding
  2. ``.claude/skills/speckit-*/SKILL.md``      -- the project-local /speckit-*
                                                  command skills (claude integration)

These are *project-local* skill files under the target, not the human's global
``~/.claude`` skills.

EVIDENCE IS NOT EXECUTION PROOF. Presence of both signals means the commands are
*installed*; it does NOT prove ``claude`` will execute them. Live execution proof
remains separately gated behind proof_e2e_v0.py ``--live`` (env HLDSPEC_LIVE_E2E=1
*and* a passing smoke). This probe is propose-only diagnostics: it classifies
evidence and stops.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_TARGET = "/tmp/proof-target"

SPECIFY_DIR = ".specify"
SKILL_GLOB = ".claude/skills/speckit-*/SKILL.md"

SKILL_EVIDENCE_PRESENT = "SKILL_EVIDENCE_PRESENT"
SKILL_EVIDENCE_MISSING = "SKILL_EVIDENCE_MISSING"

LIVE_PROOF_GATE = "proof_e2e_v0.py --live (requires HLDSPEC_LIVE_E2E=1 and a passing smoke)"

DISCLAIMER = (
    "Filesystem evidence is not execution proof. The presence of .specify/ and "
    ".claude/skills/speckit-*/SKILL.md shows the /speckit-* commands are installed; "
    "it does NOT prove `claude` will execute them. Live execution proof remains "
    f"separately gated behind {LIVE_PROOF_GATE}. This probe is read-only and "
    "propose-only: it mutates nothing in the target and runs no subprocess."
)


def probe_skill_evidence(target: str | Path) -> dict[str, Any]:
    """Read-only: classify on-disk SpecKit skill evidence for ``target``.

    Pure over the filesystem -- stats ``.specify/`` and globs
    ``.claude/skills/speckit-*/SKILL.md``. A missing target resolves to
    SKILL_EVIDENCE_MISSING (empty glob, no ``.specify/``) rather than raising. Writes
    nothing and runs no subprocess, so any path is safe to probe; unlike the live
    doctor there is no temp-root refusal because there is nothing to mutate.
    """
    target = Path(target)

    specify_dir_present = (target / SPECIFY_DIR).is_dir()
    skill_files = sorted(
        str(p.relative_to(target))
        for p in target.glob(SKILL_GLOB)
        if p.is_file()
    )
    speckit_skills_present = bool(skill_files)

    # Both independent signals are required: .specify/ alone is a SpecKit init with no
    # claude integration; skill files alone is an integration without the workflow
    # scaffolding. Either-only is SKILL_EVIDENCE_MISSING, but both booleans are exposed so
    # the partial case is visible without inventing a third verdict tier.
    verdict = (
        SKILL_EVIDENCE_PRESENT
        if specify_dir_present and speckit_skills_present
        else SKILL_EVIDENCE_MISSING
    )

    return {
        "tool": "proof_speckit_skill_evidence",
        "version": 0,
        "target": str(target),
        "specify_dir_present": specify_dir_present,
        "speckit_skills_present": speckit_skills_present,
        "speckit_skill_files": skill_files,
        "specify_dir_probed": SPECIFY_DIR,
        "skill_glob": SKILL_GLOB,
        "verdict": verdict,
        "live_proof_gate": LIVE_PROOF_GATE,
        "mutated_target": False,
        "ran_subprocess": False,
        "disclaimer": DISCLAIMER,
    }


def summarize(report: dict[str, Any]) -> str:
    lines = [
        f"# SpecKit Skill Evidence (non-stateful) -- {report['verdict']}",
        "",
        f"- target: {report['target']}",
        f"- .specify/ present: {report['specify_dir_present']}",
        f"- /speckit-* skill files present: {report['speckit_skills_present']}",
        f"- skill glob: {report['skill_glob']}",
    ]
    if report["speckit_skill_files"]:
        lines.append("- matched skill files:")
        lines += [f"    - {f}" for f in report["speckit_skill_files"]]
    lines += ["", report["disclaimer"], ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Non-stateful SpecKit skill evidence probe (read-only, mutates nothing).",
    )
    parser.add_argument("--target", default=DEFAULT_TARGET)
    parser.add_argument("--json", action="store_true", help="print the raw JSON report")
    args = parser.parse_args(argv)

    report = probe_skill_evidence(args.target)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(summarize(report))
    return 0 if report["verdict"] == SKILL_EVIDENCE_PRESENT else 1


if __name__ == "__main__":
    raise SystemExit(main())
