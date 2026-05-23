#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Checkpoint safety contract:
# Continue to target-spec generation
# Judge/orchestrator updates:
# Conversion decisions are still TBD
# Continuation protocol:
# SpecKit prework approval gate
# Do not write specs manually from HLDspec
# Do not invoke SpecKit until the human approves this gate

if command -v uv >/dev/null 2>&1; then
  export UV_CACHE_DIR="${UV_CACHE_DIR:-$PWD/.hldspec-uv-cache}"
  PYTHON_RUN=(uv run python)
else
  PYTHON_RUN=(python3)
fi

usage() {
  cat <<'EOF'
Usage:
  project_continue.sh <path-to-HLD.md> [workspace]

Default workspace:
  $PWD/.hldspec-first-run

Runs/continues HLDspec to the next safe checkpoint.
Never modifies the source HLD.
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ] || [ "$#" -lt 1 ]; then
  usage
  exit 0
fi

SOURCE_HLD="$1"
WORK="${2:-$PWD/.hldspec-first-run}"
FIRSTRUN="$WORK/firstrun"

if [ ! -f "$SOURCE_HLD" ]; then
  echo "ERROR: source HLD not found: $SOURCE_HLD" >&2
  exit 1
fi

echo "HLDspec continue"
echo "- source HLD: $SOURCE_HLD"
echo "- workspace: $WORK"
echo

is_converted_hld() {
  local hld="$1"
  [ -f "$hld" ] && grep -qE '^## HLD-[0-9]{3} - ' "$hld"
}

queue_has_tbd() {
  local queue="$1"
  "${PYTHON_RUN[@]}" - "$queue" <<'PY'
import json
import sys
from pathlib import Path

queue = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for q in queue.get("questions", []):
    if isinstance(q, dict) and q.get("blocking", True) and str(q.get("human_decision", "TBD")) == "TBD":
        sys.exit(2)
sys.exit(0)
PY
}

render_checkpoint() {
  local checkpoint="$1"
  shift
  set +e
  "${PYTHON_RUN[@]}" "$ROOT/scripts/render_hldspec_checkpoint.py" --checkpoint "$checkpoint" "$@"
  local rc=$?
  set -e
  return "$rc"
}

rebuild_post_plan_artifacts() {
  "${PYTHON_RUN[@]}" "$ROOT/scripts/review_spec_build_plan.py" "$FIRSTRUN/.specify/sync/spec_build_plan.json"
  "${PYTHON_RUN[@]}" "$ROOT/scripts/build_spec_plan_decision_queue.py" "$FIRSTRUN/.specify/sync/spec_build_plan.json" "$FIRSTRUN"
  "${PYTHON_RUN[@]}" "$ROOT/scripts/build_speckit_prework_plan.py" "$FIRSTRUN/.specify/sync/spec_build_plan.json" "$FIRSTRUN"
  "${PYTHON_RUN[@]}" "$ROOT/scripts/build_speckit_prework_quality_review.py" "$FIRSTRUN"
  "${PYTHON_RUN[@]}" "$ROOT/scripts/build_speckit_proxy_dossier.py" "$FIRSTRUN"
  "${PYTHON_RUN[@]}" "$ROOT/scripts/build_hldspec_junior_task_packets.py" "$FIRSTRUN"
  "${PYTHON_RUN[@]}" "$ROOT/scripts/build_speckit_product_manager_pack.py" "$FIRSTRUN"
  "${PYTHON_RUN[@]}" "$ROOT/scripts/build_speckit_architect_pack.py" "$FIRSTRUN"
  "${PYTHON_RUN[@]}" "$ROOT/scripts/build_speckit_answer_pack.py" "$FIRSTRUN"
  "${PYTHON_RUN[@]}" "$ROOT/scripts/build_hld_answer_dossier.py" "$FIRSTRUN"
  "${PYTHON_RUN[@]}" "$ROOT/scripts/build_speckit_constitution_from_contracts.py" "$FIRSTRUN"
  "${PYTHON_RUN[@]}" "$ROOT/scripts/build_speckit_prework_quality_review.py" "$FIRSTRUN"
  "${PYTHON_RUN[@]}" "$ROOT/scripts/build_hldspec_orchestration_state.py" "$FIRSTRUN"
  "${PYTHON_RUN[@]}" "$ROOT/scripts/build_hldspec_state.py" "$FIRSTRUN" --source-hld "$SOURCE_HLD"
  "${PYTHON_RUN[@]}" "$ROOT/scripts/build_speckit_prework_package.py" "$FIRSTRUN"
  "${PYTHON_RUN[@]}" "$ROOT/scripts/build_target_spec_work_order.py" "$FIRSTRUN/.specify/sync/spec_build_plan.json" "$FIRSTRUN"
  "${PYTHON_RUN[@]}" "$ROOT/scripts/build_spec_branch_queue.py" "$FIRSTRUN/.specify/sync/target_spec_work_order.json" "$FIRSTRUN"
}

report_spec_gate() {
  local review="$FIRSTRUN/.specify/sync/spec_build_plan_review.md"
  local plan="$FIRSTRUN/.specify/sync/spec_build_plan.json"
  local prework_review="$FIRSTRUN/.specify/sync/speckit_prework_quality_review.json"

  if [ ! -f "$review" ]; then
    return 1
  fi

  echo "State: first-run review exists."
  echo "- review: $review"
  echo "- plan: $plan"
  echo "- decision queue: $FIRSTRUN/.specify/sync/spec_build_plan_decision_queue.md"
  echo "- SpecKit input manifest: $FIRSTRUN/.specify/sync/speckit_input_manifest.md"
  echo "- SpecKit invocation queue: $FIRSTRUN/.specify/sync/speckit_invocation_queue.md"
  echo "- constitution update plan: $FIRSTRUN/.specify/sync/constitution_update_plan.md"
  echo "- feature dependency graph: $FIRSTRUN/.specify/sync/feature_dependency_graph.md"
  echo "- SpecKit prework quality review: $FIRSTRUN/.specify/sync/speckit_prework_quality_review.md"
  echo "- SpecKit proxy dossier: $FIRSTRUN/.specify/sync/speckit_proxy_dossier.md"
  echo "- SpecKit prework package: $FIRSTRUN/.specify/sync/speckit_prework_package.md"
  echo "- SpecKit Answer Dossier: $FIRSTRUN/.specify/sync/speckit_answer_dossier.md"
  echo "- Answer Dossier quality review: $FIRSTRUN/.specify/sync/hld_answer_dossier_quality_review.md"
  echo "- Interface contract map: $FIRSTRUN/.specify/sync/interface_contract_map.md"
  echo "- HLDspec state: $FIRSTRUN/.specify/sync/hldspec_state.md"
  echo

  "${PYTHON_RUN[@]}" - "$review" "$plan" "$prework_review" "$ROOT/scripts/render_hldspec_checkpoint.py" "$FIRSTRUN" <<'PY'
import json
import re
import subprocess
import sys
from pathlib import Path

review = Path(sys.argv[1])
plan_path = Path(sys.argv[2])
prework_path = Path(sys.argv[3])
renderer = Path(sys.argv[4])
workspace = Path(sys.argv[5])

text = review.read_text(encoding="utf-8", errors="replace")
plan = json.loads(plan_path.read_text(encoding="utf-8")) if plan_path.exists() else {}
pq = plan.get("plan_quality", {}) if isinstance(plan, dict) else {}

decision = pq.get("decision", "")
recommendation = pq.get("recommendation", "")
conflicts = pq.get("conflicts", [])
planned = plan.get("planned_specs", []) if isinstance(plan, dict) else []
bad = []
for spec in planned:
    if isinstance(spec, dict) and (spec.get("quality_flags") or spec.get("requires_user_review")):
        bad.append(spec.get("planned_spec_id"))

continue_true = bool(re.search(r"Continue to target-spec generation:\s*`?true`?", text, re.I))
continue_false = bool(re.search(r"Continue to target-spec generation:\s*`?false`?", text, re.I))
plan_green = continue_true and not continue_false and decision in {"PASS", "FIX", "HANDLED"} and recommendation == "KEEP_PLAN" and not conflicts and not bad

print(f"Plan quality decision: {decision}")
print(f"Recommendation: {recommendation}")
print(f"Planned specs: {len(planned)}")
print(f"Conflicts: {len(conflicts)}")
print(f"Flagged specs: {len(bad)}")
print(f"Plan gate green: {plan_green}")
print()

def render(checkpoint: str, code: int) -> None:
    cmd = [sys.executable, str(renderer), "--checkpoint", checkpoint, "--workspace", str(workspace)]
    if checkpoint == "SPEC_BUILD_PLAN_CHECKPOINT":
        cmd.extend(["--plan", str(plan_path), "--review", str(review)])
    if checkpoint in {"SPECKIT_PREWORK_REWORK", "SPECKIT_PREWORK_APPROVAL_GATE"}:
        cmd.extend(["--prework-review", str(prework_path)])
    subprocess.run(cmd, check=False)
    sys.exit(code)

if not plan_green:
    render("SPEC_BUILD_PLAN_CHECKPOINT", 2)

if not prework_path.exists():
    render("SPECKIT_PREWORK_MISSING", 2)

prework = json.loads(prework_path.read_text(encoding="utf-8")) if prework_path.exists() else {}
prework_status = prework.get("status", "MISSING")
findings = prework.get("findings", [])
blockers = [item for item in findings if isinstance(item, dict) and item.get("severity") == "BLOCKER"]

print(f"SpecKit prework quality status: {prework_status}")
print(f"SpecKit prework findings: {len(findings)}")
print(f"SpecKit prework blockers: {len(blockers)}")
print()

if prework_status == "REWORK_REQUIRED" or blockers:
    render("SPECKIT_PREWORK_REWORK", 2)

render("SPECKIT_PREWORK_APPROVAL_GATE", 0)
PY
}

# 1. Initial run if workspace does not exist.
if [ ! -f "$WORK/HLD.md" ]; then
  echo "State: no working HLD found. Running read-only first run."
  set +e
  bash "$ROOT/scripts/project_first_run.sh" "$SOURCE_HLD" "$WORK"
  rc=$?
  set -e
  exit "$rc"
fi

# 2. Stop at unanswered conversion checkpoint.
QUEUE="$WORK/.specify/sync/hld_conversion_decision_queue.json"
if [ -f "$QUEUE" ]; then
  set +e
  queue_has_tbd "$QUEUE"
  qrc=$?
  set -e
  if [ "$qrc" -eq 2 ]; then
    "${PYTHON_RUN[@]}" "$ROOT/scripts/write_hld_decision_log.py" "$WORK" --source-hld "$SOURCE_HLD"
    "${PYTHON_RUN[@]}" "$ROOT/scripts/write_hld_source_update_queue.py" "$WORK" --source-hld "$SOURCE_HLD"
    echo "State: human checkpoint required."
    echo
    render_checkpoint HLD_CONVERSION_DECISIONS \
      --queue "$QUEUE" \
      --workspace "$WORK" \
      --source-hld "$SOURCE_HLD" \
      --runner "$ROOT/scripts/hldspec_run.sh"
    exit "$?"
  elif [ "$qrc" -ne 0 ]; then
    echo "ERROR: failed to inspect decision queue." >&2
    exit "$qrc"
  fi
fi

# 3. Apply answered conversion decisions if working HLD is still raw.
if ! is_converted_hld "$WORK/HLD.md"; then
  if [ -f "$QUEUE" ]; then
    echo "State: conversion decisions are answered and working HLD is raw. Recording decisions and applying conversion."
    "${PYTHON_RUN[@]}" "$ROOT/scripts/write_hld_decision_log.py" "$WORK" --source-hld "$SOURCE_HLD"
    "${PYTHON_RUN[@]}" "$ROOT/scripts/write_hld_source_update_queue.py" "$WORK" --source-hld "$SOURCE_HLD"
    "${PYTHON_RUN[@]}" "$ROOT/scripts/apply_hld_conversion_decisions.py" "$WORK/HLD.md" "$QUEUE"
  else
    echo "State: working HLD is raw and no decision queue exists. Running initial first run again."
    set +e
    bash "$ROOT/scripts/project_first_run.sh" "$SOURCE_HLD" "$WORK"
    rc=$?
    set -e
    exit "$rc"
  fi
fi

# 4. Run first-readonly on converted working HLD if needed.
if [ ! -f "$FIRSTRUN/.specify/sync/spec_build_plan_review.md" ]; then
  echo "State: working HLD is converted. Running first-readonly on converted HLD."
  bash "$ROOT/scripts/first_run_readonly.sh" "$WORK/HLD.md" "$FIRSTRUN" --force
fi

# 4.5. Apply answered spec-build-plan decisions to the workspace plan.
SPEC_PLAN_QUEUE="$FIRSTRUN/.specify/sync/spec_build_plan_decision_queue.json"
SPEC_PLAN="$FIRSTRUN/.specify/sync/spec_build_plan.json"
if [ -f "$SPEC_PLAN_QUEUE" ] && [ -f "$SPEC_PLAN" ]; then
  set +e
  queue_has_tbd "$SPEC_PLAN_QUEUE"
  spq_rc=$?
  set -e
  if [ "$spq_rc" -eq 0 ]; then
    echo "State: spec build plan decision queue has no TBD answers. Applying decisions to workspace plan."
    "${PYTHON_RUN[@]}" "$ROOT/scripts/apply_spec_build_plan_decisions.py" "$FIRSTRUN"
    rebuild_post_plan_artifacts
  elif [ "$spq_rc" -ne 2 ]; then
    echo "ERROR: failed to inspect spec build plan decision queue." >&2
    exit "$spq_rc"
  fi
fi

# 5. Report spec gate.
report_spec_gate
