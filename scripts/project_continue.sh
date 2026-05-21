#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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

print_decision_queue() {
  local queue="$1"
  "${PYTHON_RUN[@]}" - "$queue" <<'PY'
import json
import sys
from pathlib import Path

queue = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
checkpoint = queue.get("checkpoint", {})
questions = queue.get("questions", [])

print(f"Checkpoint: {checkpoint.get('checkpoint_id', 'HLD_CONVERSION_DECISIONS')}")
print(f"Allowed to convert: {checkpoint.get('allowed_to_convert', False)}")
print(f"Open questions: {checkpoint.get('open_question_count', len(questions))}")
print()

for q in questions:
    if not isinstance(q, dict):
        continue
    print(f"{q.get('question_id')} {q.get('source_candidate_id')} - {q.get('title')}")
    print(f"Question: {q.get('question')}")
    print("Options: " + ", ".join(q.get("options", [])))
    print(f"Human decision: {q.get('human_decision')}")
    print()
PY
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
  echo

  "${PYTHON_RUN[@]}" - "$review" "$plan" "$prework_review" <<'PY'
import json
import re
import sys
from pathlib import Path

review = Path(sys.argv[1])
plan_path = Path(sys.argv[2])
prework_path = Path(sys.argv[3])

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
plan_green = continue_true and not continue_false and decision == "FIX" and recommendation == "KEEP_PLAN" and not conflicts and not bad

print(f"Plan quality decision: {decision}")
print(f"Recommendation: {recommendation}")
print(f"Planned specs: {len(planned)}")
print(f"Conflicts: {len(conflicts)}")
print(f"Flagged specs: {len(bad)}")
print(f"Plan gate green: {plan_green}")

if not plan_green:
    print()
    print("Next safe checkpoint: Spec Build Plan is blocked.")
    print("Review spec_build_plan_review.md and spec_build_plan_decision_queue.md.")
    sys.exit(2)

prework = json.loads(prework_path.read_text(encoding="utf-8")) if prework_path.exists() else {}
prework_status = prework.get("status", "MISSING")
findings = prework.get("findings", [])
blockers = [item for item in findings if isinstance(item, dict) and item.get("severity") == "BLOCKER"]

print(f"SpecKit prework quality status: {prework_status}")
print(f"SpecKit prework findings: {len(findings)}")
print(f"SpecKit prework blockers: {len(blockers)}")
print()

if not prework_path.exists():
    print("Next safe checkpoint: SpecKit prework artifacts are missing.")
    print("Rerun first_readonly to regenerate SpecKit prework artifacts.")
    sys.exit(2)

if prework_status == "REWORK_REQUIRED" or blockers:
    print("Next safe checkpoint: SpecKit prework requires rework.")
    print("Review speckit_prework_quality_review.md, rebuild affected artifacts, and rerun the quality gate.")
    sys.exit(2)

print("Next safe checkpoint: SpecKit prework approval gate.")
print("Present speckit_prework_quality_review.md and speckit_proxy_dossier.md to the human.")
print("Explain the constitution case, architecture/dependency case, first-feature case, Beskeptic findings, and feedback impact rules.")
print("Do not write specs manually from HLDspec.")
print("Do not invoke SpecKit until the human approves this gate.")
sys.exit(0)
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
    echo "State: human checkpoint required. Conversion decisions are still TBD."
    echo
    print_decision_queue "$QUEUE"
    echo "Open:"
    echo "- $WORK/.specify/sync/hld_conversion_decision_queue.md"
    echo
    echo "Continuation protocol:"
    echo "- Human answers only the listed checkpoint questions."
    echo "- Judge/orchestrator updates: $WORK/.specify/sync/hld_conversion_decision_queue.json"
    echo "- Then reruns the same command: $ROOT/scripts/hldspec_run.sh $SOURCE_HLD"
    exit 2
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

# 5. Report spec gate.
report_spec_gate
