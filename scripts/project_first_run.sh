#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  project_first_run.sh <path-to-HLD.md> [workspace]

Run from a project repository.

Default workspace:
  $PWD/.hldspec-first-run

What this does:
  project HLD
  -> read-only HLDspec first run
  -> conversion plan if raw
  -> decision queue if human checkpoint is needed
  -> spec build plan review if HLDspec-ready

It never edits the source HLD.
It never calls an agent.
It never creates specs or implementation files.
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ] || [ "$#" -lt 1 ]; then
  usage
  exit 0
fi

HLD="$1"
WORK="${2:-$PWD/.hldspec-first-run}"

if [ ! -f "$HLD" ]; then
  echo "ERROR: HLD file not found: $HLD" >&2
  echo "Hint: run from the project repo and pass the HLD path, for example:" >&2
  echo "  ~/code/HLDspec/scripts/project_first_run.sh ./Flow-System-HLD.md" >&2
  exit 1
fi

set +e
bash "$ROOT/scripts/first_run_readonly.sh" "$HLD" "$WORK" --force
rc=$?
set -e

echo
echo "Project first-run wrapper summary"
echo "- workspace: $WORK"
echo "- exit code: $rc"

if [ "$rc" -eq 2 ]; then
  echo "- state: raw HLD / conversion checkpoint"

  if [ -f "$WORK/.specify/sync/hld_conversion_decision_queue.json" ]; then
    python3 - "$WORK/.specify/sync/hld_conversion_decision_queue.json" <<'PY'
import json
import sys
from pathlib import Path

queue = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
checkpoint = queue.get("checkpoint", {})
print(f"- checkpoint: {checkpoint.get('checkpoint_id', 'UNKNOWN')}")
print(f"- allowed to convert: {checkpoint.get('allowed_to_convert', False)}")
print(f"- open questions: {checkpoint.get('open_question_count', 0)}")
for question in queue.get("questions", []):
    print()
    print(f"{question.get('question_id')} {question.get('source_candidate_id')} - {question.get('title')}")
    print(f"Question: {question.get('question')}")
    print("Options: " + ", ".join(question.get("options", [])))
    print(f"Human decision: {question.get('human_decision')}")
PY
  fi

  echo
  echo "Open:"
  echo "- $WORK/.specify/sync/hld_conversion_plan.md"
  echo "- $WORK/.specify/sync/hld_conversion_decision_queue.md"
  echo "- $WORK/HLD_CONVERSION_PROMPT.md"
  exit 2
fi

if [ "$rc" -eq 0 ]; then
  echo "- state: HLDspec-ready first run complete"
  echo
  echo "Open:"
  echo "- $WORK/.specify/sync/spec_build_plan_review.md"
  echo "- $WORK/.specify/sync/spec_build_plan.md"
  exit 0
fi

echo "- state: error"
exit "$rc"
