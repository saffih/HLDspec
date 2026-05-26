#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_FIRST_READ = [
    "AGENTS.md",
    "CLAUDE.md",
    "TASKS.md",
    "docs/HLDSPEC_DEVELOPMENT_HANDOFF.md",
    "docs/HLDSPEC_DEVELOPMENT_BACKLOG.md",
    "docs/DOCS_INDEX.md",
    "docs/CANONICAL_FLOW.md",
    "docs/ARCHITECTURE_V2.md",
    "docs/HLDSPEC_STABILITY_ARCHITECTURE.md",
]

INVARIANTS = [
    "Source HLD is read-only. Workspace copy only.",
    "SpecKit is not invoked until approval gates pass.",
    "Final SpecKit specs are not written manually by HLDspec.",
    "Application code is not implemented by HLDspec.",
    "Gate machines gate; scripts generate.",
    "Dependency graph and invocation queue must not diverge.",
    "RunSkeptic must use the real current skeptic.md.",
    "Patch scripts must be syntax checked before handoff.",
    "Dirty-tree work must be handled explicitly.",
    "HLDspec runtime state belongs outside core code.",
    "Durable backlog belongs in docs/HLDSPEC_DEVELOPMENT_BACKLOG.md.",
]

DO_NOT_DO = [
    "Do not depend on hidden chat history.",
    "Do not rerun a failed patch blindly.",
    "Do not reset or delete dirty work without explicit approval.",
    "Do not treat archived docs as authoritative.",
    "Do not update final SpecKit specs manually from HLDspec.",
    "Do not implement app code inside HLDspec.",
    "Do not approve architecture, source-of-truth, contract, or gate changes without RunSkeptic or human approval.",
]


@dataclass(frozen=True)
class HandoffPacket:
    handoff_id: str
    created_at: str
    repo: str
    from_actor: str
    to_actor: str
    model_tier: str
    focus: str
    current_branch: str
    current_head: str
    git_status: list[str]
    last_commits: list[str]
    canonical_handoff_protocol: str
    canonical_backlog: str
    required_first_read: list[str]
    changed_files: list[str]
    relevant_files: list[str]
    invariants: list[str]
    tests_run: list[str]
    tests_required: list[str]
    runskeptic_status: str
    open_actions: list[str]
    open_conflicts: list[str]
    next_safe_step: str
    do_not_do: list[str]


def run_git(repo: Path, args: list[str]) -> list[str]:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "").strip()
        return [f"git {' '.join(args)} failed: {message}"]
    return [line for line in result.stdout.splitlines() if line.strip()]


def changed_files_from_status(status: list[str]) -> list[str]:
    files: list[str] = []
    for line in status:
        if not line.strip() or line.startswith("git "):
            continue
        files.append(line[3:].strip() if len(line) > 3 else line.strip())
    return sorted(set(files))


def build_packet(args: argparse.Namespace) -> HandoffPacket:
    repo = Path(args.repo).expanduser().resolve()
    status = run_git(repo, ["status", "--short"])
    changed = changed_files_from_status(status)
    relevant = list(dict.fromkeys([*REQUIRED_FIRST_READ, *changed]))
    now = datetime.now(timezone.utc)
    handoff_id = args.handoff_id or f"hldspec-dev-{now.strftime('%Y%m%dT%H%M%SZ')}"

    return HandoffPacket(
        handoff_id=handoff_id,
        created_at=now.isoformat(timespec="seconds"),
        repo=str(repo),
        from_actor=args.from_agent,
        to_actor=args.to_agent,
        model_tier=args.model_tier,
        focus=args.focus,
        current_branch=(run_git(repo, ["branch", "--show-current"]) or ["UNKNOWN"])[0],
        current_head=(run_git(repo, ["rev-parse", "--short", "HEAD"]) or ["UNKNOWN"])[0],
        git_status=status,
        last_commits=run_git(repo, ["log", "--oneline", "-5"]),
        canonical_handoff_protocol="docs/HLDSPEC_DEVELOPMENT_HANDOFF.md",
        canonical_backlog="docs/HLDSPEC_DEVELOPMENT_BACKLOG.md",
        required_first_read=list(REQUIRED_FIRST_READ),
        changed_files=changed,
        relevant_files=relevant,
        invariants=list(INVARIANTS),
        tests_run=[item for item in args.tests_run if item],
        tests_required=[
            "git diff --check",
            "python3 -m py_compile scripts/hldspec_dev_handoff.py",
            "python3 -m unittest discover -s tests_v2 -v",
        ],
        runskeptic_status=args.runskeptic_status,
        open_actions=[item for item in args.open_action if item],
        open_conflicts=[item for item in args.open_conflict if item],
        next_safe_step=args.next_safe_step,
        do_not_do=list(DO_NOT_DO),
    )


def bullets(items: list[str]) -> str:
    return "".join(f"- {item}\n" for item in items) if items else "- none\n"


def render_markdown(packet: HandoffPacket) -> str:
    return f"""# HLDspec Development Handoff

## Canonical references

- Handoff protocol: `{packet.canonical_handoff_protocol}`
- Durable backlog: `{packet.canonical_backlog}`

This packet is current-session state only. Do not treat it as the protocol or backlog.

## Summary

- Handoff ID: `{packet.handoff_id}`
- Created at: `{packet.created_at}`
- Repo: `{packet.repo}`
- From: `{packet.from_actor}`
- To: `{packet.to_actor}`
- Model tier: `{packet.model_tier}`
- Focus: {packet.focus}
- Branch: `{packet.current_branch}`
- HEAD: `{packet.current_head}`

## Required first read

{bullets(packet.required_first_read)}
## Current git status

```text
{chr(10).join(packet.git_status) if packet.git_status else "clean"}
```

## Last commits

```text
{chr(10).join(packet.last_commits) if packet.last_commits else "none"}
```

## Changed files

{bullets(packet.changed_files)}
## Relevant files for next model

{bullets(packet.relevant_files)}
## Invariants

{bullets(packet.invariants)}
## Tests already run

{bullets(packet.tests_run)}
## Tests required before promotion

{bullets(packet.tests_required)}
## RunSkeptic status

{packet.runskeptic_status}

## Open ACTION items

{bullets(packet.open_actions)}
## Open CONFLICT items

{bullets(packet.open_conflicts)}
## Next safe step

{packet.next_safe_step}

## Do not do

{bullets(packet.do_not_do)}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an HLDspec repo-development handoff packet.")
    parser.add_argument("--repo", default=".", help="HLDspec repo path.")
    parser.add_argument("--out-dir", default=".hldspec-dev/handoff", help="Output directory.")
    parser.add_argument("--handoff-id", default="")
    parser.add_argument("--from-agent", default="unknown")
    parser.add_argument("--to-agent", default="next-agent")
    parser.add_argument("--model-tier", default="MODEL_DEFAULT", choices=["MODEL_ROUTINE", "MODEL_DEFAULT", "MODEL_STRONG", "MODEL_CRITICAL", "HUMAN"])
    parser.add_argument("--focus", required=True)
    parser.add_argument("--tests-run", action="append", default=[])
    parser.add_argument("--runskeptic-status", default="NOT_RUN")
    parser.add_argument("--open-action", action="append", default=[])
    parser.add_argument("--open-conflict", action="append", default=[])
    parser.add_argument("--next-safe-step", default="Read required first-read docs, inspect git status, then continue only within the stated focus.")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not (repo / ".git").exists():
        raise SystemExit(f"ERROR: not a git repo: {repo}")

    packet = build_packet(args)
    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "HANDOFF.json"
    md_path = out_dir / "HANDOFF.md"
    json_path.write_text(json.dumps(asdict(packet), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(packet), encoding="utf-8")

    print(f"Wrote: {md_path}")
    print(f"Wrote: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
