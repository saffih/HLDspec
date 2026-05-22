#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def run(command: list[str], cwd: Path) -> dict[str, Any]:
    proc = subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return {
        "name": " ".join(command),
        "command": command,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
        "status": "PASS" if proc.returncode == 0 else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the HLDspec V2 readiness gate.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--output-dir", default=".hldspec-v2-ready-gate")
    parser.add_argument("--fail-on-not-ready", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    out = Path(args.output_dir)
    if not out.is_absolute():
        out = repo / out
    out.mkdir(parents=True, exist_ok=True)

    required = [
        "tests_v2/test_role_review_machine.py",
        "tests_v2/test_agent_roles_doc.py",
        "docs/HLDSPEC_V2_AGENT_ROLES.md",
        "tests_v2/test_raw_hld_chunk_scan.py",
        "docs/HLDSPEC_V2_ROLE_REVIEWS.md",
        "hldspec/machines/role_review.py",
        "hldspec/role_review_contract.py",
        "hldspec/raw_hld.py",
        "docs/ARCHITECTURE_V2.md",
        "docs/TEST_STRATEGY_V2.md",
        "docs/TODO_V2.md",
        "hldspec/state_machine.py",
        "hldspec/result_renderer.py",
        "hldspec/command_runner.py",
        "hldspec/machines/raw_hld_conversion.py",
        "hldspec/machines/apply_hld_conversion.py",
        "hldspec/machines/spec_build_plan.py",
        "hldspec/machines/speckit_prework.py",
        "hldspec/machines/approval_gate.py",
        "hldspec/machines/project.py",
        "scripts/hldspec_v2.py",
        "tests_v2/test_state_machine_contract.py",
        "tests_v2/test_machine_result_renderer.py",
        "tests_v2/test_raw_hld_conversion_machine.py",
        "tests_v2/test_v2_full_slice.py",
        "tests_v2/test_hldspec_v2_flow_test_doc.py",
        "tests_v2/test_answer_conversion_queue.py",
        "tests_v2/test_spec_build_plan_debug.py",
        "tests_v2/test_spec_build_plan_gate_decision.py",
        "tests_v2/test_approval_gate_handoff_docs.py",
        "tests_v2/test_handoff_docs.py",
        "docs/HLDSPEC_V2_HANDOFF_DOCS.md",
        "hldspec/handoff_docs.py",
        "docs/HLDSPEC_V2_SPEC_PLAN_GATE_DECISION.md",
        "scripts/hldspec_v2_answer_spec_plan_gate.py",
        "docs/HLDSPEC_V2_SPEC_PLAN_DEBUG.md",
        "tests_v2/test_apply_hld_conversion_debug.py",
        "docs/HLDSPEC_V2_APPLY_DEBUG.md",
        "scripts/hldspec_v2_answer_conversion_queue.py",
        "tests_v2/test_hldspec_v2_flow_test_runner.py",
        "docs/HLDSPEC_V2_FLOW_TEST.md",
        "scripts/hldspec_v2_flow_test.sh",
        "scripts/hldspec_v2_flow_test.py",
    ]

    checks: list[dict[str, Any]] = []
    missing = [item for item in required if not (repo / item).exists()]
    checks.append({"name": "required_files", "status": "PASS" if not missing else "FAIL", "missing": missing})
    checks.append({"name": "legacy_tests_moved_aside", "status": "PASS" if (repo / "tests_legacy").exists() else "FAIL"})
    checks.append(run([sys.executable, "-m", "unittest", "discover", "-s", "tests_v2", "-v"], repo))

    status = "READY_FOR_V2_REWRITE" if all(check["status"] == "PASS" for check in checks) else "NOT_READY"
    report = {"schema_version": 1, "status": status, "checks": checks}

    (out / "hldspec_v2_ready_gate.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "hldspec_v2_ready_gate.md").write_text(
        "# HLDspec V2 Ready Gate\n\n"
        "made by AI\n\n"
        f"Status: `{status}`\n\n"
        "This gate runs only V2 tests under `tests_v2/`.\n"
        "Legacy tests are preserved under `tests_legacy/` and are not active in this gate.\n",
        encoding="utf-8",
    )

    print(f"HLDspec V2 Ready Gate: {status}")
    print(f"- json: {out / 'hldspec_v2_ready_gate.json'}")
    print(f"- report: {out / 'hldspec_v2_ready_gate.md'}")
    if args.fail_on_not_ready and status != "READY_FOR_V2_REWRITE":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
