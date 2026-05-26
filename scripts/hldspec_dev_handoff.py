#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_FIRST_READ = [
    "CLAUDE.md",
    "TASKS.md",
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
]

DO_NOT_DO = [
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
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "").strip()
        return [f"git {' '.join(args)} failed: {message}"]
    return [line for line in result.stdout.splitlines() if line.strip()]


def current_branch(repo: Path) -> str:
    out = run_git(repo, ["branch", "--show-current"])
    return out[0] if out else "UNKNOWN"


def current_head(repo: Path) -> str:
    out = run_git(repo, ["rev-parse", "--short", "HEAD"])
    return out[0] if out else "UNKNOWN"


def changed_files_from_status(status: list[str]) -> list[str]:
    files: list[str] = []
    for line in status:
        if not line.strip() or line.startswith("git "):
            continue
        # porcelain short: XY path
        files.append(line[3:].strip() if len(line) > 3 else line.strip())
    return sorted(set(files))


def build_packet(args: argparse.Namespace) -> HandoffPacket:
    repo = Path(args.repo).expanduser().resolve()
    status = run_git(repo, ["status", "--short"])
    commits = run_git(repo, ["log", "--oneline", "-5"])
    changed = changed_files_from_status(status)

    relevant = list(REQUIRED_FIRST_READ)
    for path in changed:
        if path and path not in relevant:
            relevant.append(path)

    tests_required = [
        "python3 -m unittest discover -s tests_v2 -v",
        "python3 -m pytest tests_v2 -q",
        "git diff --check",
    ]

    handoff_id = args.handoff_id or f"hldspec-dev-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    return HandoffPacket(
        handoff_id=handoff_id,
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        repo=str(repo),
        from_actor=args.from_agent,
        to_actor=args.to_agent,
        model_tier=args.model_tier,
        focus=args.focus,
        current_branch=current_branch(repo),
        current_head=current_head(repo),
        git_status=status,
        last_commits=commits,
        required_first_read=list(REQUIRED_FIRST_READ),
        changed_files=changed,
        relevant_files=relevant,
        invariants=list(INVARIANTS),
        tests_run=[item for item in args.tests_run if item],
        tests_required=tests_required,
        runskeptic_status=args.runskeptic_status,
        open_actions=[item for item in args.open_action if item],
        open_conflicts=[item for item in args.open_conflict if item],
        next_safe_step=args.next_safe_step,
        do_not_do=list(DO_NOT_DO),
    )


def render_markdown(packet: HandoffPacket) -> str:
    def bullets(items: list[str]) -> str:
        if not items:
            return "- none\n"
        return "".join(f"- {item}\n" for item in items)

    return f"""# HLDspec Development Handoff

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


def write_packet(packet: HandoffPacket, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "HANDOFF.json"
    md_path = out_dir / "HANDOFF.md"
    json_path.write_text(json.dumps(asdict(packet), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(packet), encoding="utf-8")
    return md_path, json_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an HLDspec repo-development handoff packet.")
    parser.add_argument("--repo", default=".", help="HLDspec repo path. Default: current directory.")
    parser.add_argument("--out-dir", default=".hldspec-dev/handoff", help="Output directory for HANDOFF.md/json.")
    parser.add_argument("--handoff-id", default="", help="Optional stable handoff id.")
    parser.add_argument("--from-agent", default="unknown", help="Current agent/model/person.")
    parser.add_argument("--to-agent", default="next-agent", help="Next agent/model/person.")
    parser.add_argument("--model-tier", default="MODEL_DEFAULT", choices=["MODEL_ROUTINE", "MODEL_DEFAULT", "MODEL_STRONG", "MODEL_CRITICAL", "HUMAN"])
    parser.add_argument("--focus", required=True, help="Current work focus.")
    parser.add_argument("--tests-run", action="append", default=[], help="Test/check command already run. Repeatable.")
    parser.add_argument("--runskeptic-status", default="NOT_RUN", help="RunSkeptic status: NOT_RUN/PASS/ACTION/CONFLICT plus notes.")
    parser.add_argument("--open-action", action="append", default=[], help="Open ACTION item. Repeatable.")
    parser.add_argument("--open-conflict", action="append", default=[], help="Open CONFLICT item. Repeatable.")
    parser.add_argument("--next-safe-step", default="Read required first-read docs, inspect git status, then continue only within the stated focus.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).expanduser().resolve()
    if not (repo / ".git").exists():
        raise SystemExit(f"ERROR: not a git repo: {repo}")
    packet = build_packet(args)
    md_path, json_path = write_packet(packet, Path(args.out_dir).expanduser())
    print(f"Wrote: {md_path}")
    print(f"Wrote: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
