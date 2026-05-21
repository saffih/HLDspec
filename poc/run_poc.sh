#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-/tmp/hldspec-poc}"

rm -rf "$OUT"
mkdir -p "$OUT"

echo "HLDspec POC output: $OUT"
echo

for hld in "$ROOT"/poc/hlds/*.md; do
  case_name="$(basename "$hld" .md)"
  workspace="$OUT/$case_name"

  echo "== $case_name =="
  bash "$ROOT/scripts/first_run_readonly.sh" "$hld" "$workspace" --force >/tmp/hldspec-poc-${case_name}.log

  python3 - "$workspace/.specify/sync/spec_build_plan.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
plan = json.loads(path.read_text(encoding="utf-8"))
quality = plan.get("plan_quality", {})
planned = plan.get("planned_specs", [])
flagged = [item for item in planned if item.get("quality_flags")]
print("Plan quality:", quality.get("decision"), quality.get("recommendation"))
print("Planned specs:", len(planned))
print("Flagged specs:", ", ".join(item.get("planned_spec_id", "?") for item in flagged) or "none")
print("Conflicts:", len(quality.get("conflicts", [])))
PY

  echo "Review: $workspace/.specify/sync/spec_build_plan_review.md"
  echo
done

echo "Done."
