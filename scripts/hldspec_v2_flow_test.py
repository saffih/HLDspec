#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hldspec.machines.project import ProjectMachine
from hldspec.result_renderer import machine_result_to_dict, render_machine_result
from hldspec.state_machine import MachineContext, MachineStatus


VALID_TEST_STATUSES = {
    MachineStatus.CONTINUE,
    MachineStatus.STOP_CHECKPOINT,
    MachineStatus.DONE,
}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def flow_test_status(status: MachineStatus) -> str:
    if status == MachineStatus.STOP_CHECKPOINT:
        return "CHECKPOINT_REACHED"
    if status in {MachineStatus.CONTINUE, MachineStatus.DONE}:
        return "FLOW_CONTINUES"
    if status == MachineStatus.BLOCKED:
        return "BLOCKED"
    return "ERROR"


def build_summary(*, source_hld: Path, workspace: Path, output_dir: Path, result_dict: dict[str, Any]) -> dict[str, Any]:
    checkpoint = result_dict.get("checkpoint")
    checkpoint_kind = checkpoint.get("kind") if isinstance(checkpoint, dict) else None
    human_questions = checkpoint.get("human_questions", []) if isinstance(checkpoint, dict) else []
    open_questions = [
        question
        for question in human_questions
        if isinstance(question, dict)
        and question.get("blocking", True)
        and question.get("current_decision", "TBD") == "TBD"
    ]

    return {
        "schema_version": 1,
        "source_hld": str(source_hld),
        "workspace": str(workspace),
        "output_dir": str(output_dir),
        "machine": result_dict.get("machine"),
        "state": result_dict.get("state"),
        "status": result_dict.get("status"),
        "exit_code": result_dict.get("exit_code"),
        "requires_human": result_dict.get("requires_human"),
        "flow_test_status": flow_test_status(MachineStatus(str(result_dict.get("status")))),
        "checkpoint_kind": checkpoint_kind,
        "open_question_count": len(open_questions),
        "valid_for_flow_testing": result_dict.get("status") in {status.value for status in VALID_TEST_STATUSES},
        "specKit_invoked": False,
        "source_hld_modified_by_runner": False,
        "artifacts": {
            "machine_result_json": str(output_dir / "machine_result.json"),
            "machine_result_report": str(output_dir / "machine_result.md"),
            "flow_test_summary_json": str(output_dir / "flow_test_summary.json"),
            "flow_test_summary_report": str(output_dir / "flow_test_summary.md"),
        },
    }


def render_summary_md(summary: dict[str, Any], rendered_result: str) -> str:
    lines = [
        "# HLDspec V2 Flow Test Summary",
        "",
        "made by AI",
        "",
        f"Flow test status: `{summary['flow_test_status']}`",
        f"Machine: `{summary['machine']}`",
        f"State: `{summary['state']}`",
        f"Status: `{summary['status']}`",
        f"Exit code: `{summary['exit_code']}`",
        f"Checkpoint: `{summary['checkpoint_kind']}`",
        f"Open questions: `{summary['open_question_count']}`",
        f"Valid for Flow testing: `{str(summary['valid_for_flow_testing']).lower()}`",
        "",
        "## Safety",
        "",
        "- SpecKit invoked: `false`",
        "- Source HLD modified by runner: `false`",
        "- App code implemented: `false`",
        "",
        "## Artifacts",
        "",
    ]

    for label, path in summary["artifacts"].items():
        lines.append(f"- `{label}`: `{path}`")

    lines += [
        "",
        "## MachineResult report",
        "",
        "```text",
        rendered_result.rstrip(),
        "```",
        "",
    ]

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HLDspec V2 against a Flow HLD and write test artifacts.")
    parser.add_argument("source_hld", help="Path to source HLD, e.g. ~/code/flow/Flow-System-HLD.md")
    parser.add_argument(
        "--repo",
        default=str(ROOT),
        help="HLDspec repo root. Defaults to this script's repo.",
    )
    parser.add_argument(
        "--workspace",
        default=None,
        help="Workspace. Defaults to <source-dir>/.hldspec-v2-flow-test/workspace",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output dir. Defaults to <source-dir>/.hldspec-v2-flow-test",
    )
    parser.add_argument(
        "--exit-with-result-code",
        action="store_true",
        help="Exit with the MachineResult exit code. By default checkpoints are treated as valid test outcomes.",
    )
    parser.add_argument(
        "--fail-on-blocked",
        action="store_true",
        help="Exit non-zero if the machine result is BLOCKED or ERROR.",
    )
    args = parser.parse_args()

    source_hld = Path(args.source_hld).expanduser().resolve()
    if not source_hld.exists():
        print(f"ERROR: source HLD not found: {source_hld}", file=sys.stderr)
        return 1

    repo = Path(args.repo).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else source_hld.parent / ".hldspec-v2-flow-test"
    workspace = Path(args.workspace).expanduser().resolve() if args.workspace else output_dir / "workspace"

    result = ProjectMachine().run(
        MachineContext(
            repo_root=str(repo),
            source_hld=str(source_hld),
            workspace=str(workspace),
        )
    )

    result_dict = machine_result_to_dict(result)
    rendered = render_machine_result(result)
    summary = build_summary(
        source_hld=source_hld,
        workspace=workspace,
        output_dir=output_dir,
        result_dict=result_dict,
    )

    write_json(output_dir / "machine_result.json", result_dict)
    write_text(output_dir / "machine_result.md", rendered)
    write_json(output_dir / "flow_test_summary.json", summary)
    write_text(output_dir / "flow_test_summary.md", render_summary_md(summary, rendered))

    print(f"HLDspec V2 Flow Test: {summary['flow_test_status']}")
    print(f"- source HLD: {source_hld}")
    print(f"- workspace: {workspace}")
    print(f"- summary: {output_dir / 'flow_test_summary.md'}")
    print(f"- machine result: {output_dir / 'machine_result.md'}")
    print(f"- checkpoint: {summary['checkpoint_kind']}")
    print(f"- open questions: {summary['open_question_count']}")
    print()

    print(rendered, end="")

    if args.exit_with_result_code:
        return int(result.exit_code())

    if args.fail_on_blocked and result.status not in VALID_TEST_STATUSES:
        return int(result.exit_code())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
