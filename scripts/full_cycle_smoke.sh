#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE="${1:-/tmp/hldspec-full-cycle-smoke}"
HLD_SOURCE="${2:-$ROOT/tests/fixtures/full_cycle_hld.md}"

rm -rf "$WORKSPACE"
mkdir -p "$WORKSPACE"
cp "$HLD_SOURCE" "$WORKSPACE/HLD.md"

echo "Workspace: $WORKSPACE"
echo "HLD source: $HLD_SOURCE"

python3 "$ROOT/hld_spec_sync.py" --workspace "$WORKSPACE" --hld HLD.md --hld-format-report
python3 "$ROOT/hld_spec_sync.py" --workspace "$WORKSPACE" --hld HLD.md --hld-map-only
python3 "$ROOT/hld_spec_sync.py" --workspace "$WORKSPACE" --hld HLD.md --use-hld-map --plan-specs

test -f "$WORKSPACE/.specify/sync/spec_build_plan.json"
test -f "$WORKSPACE/.specify/sync/spec_build_plan.md"

if [ -e "$WORKSPACE/.specify/memory/constitution.md" ]; then
  echo "ERROR: read-only full-cycle smoke created target constitution unexpectedly" >&2
  exit 1
fi

if find "$WORKSPACE/specs" -name spec.md -print -quit 2>/dev/null | grep -q .; then
  echo "ERROR: read-only full-cycle smoke created specs unexpectedly" >&2
  exit 1
fi

python3 - "$WORKSPACE/.specify/sync/spec_build_plan.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
plan = json.loads(path.read_text(encoding="utf-8"))

quality = plan.get("plan_quality", {})
if not quality:
    raise SystemExit("missing plan_quality")

planned = plan.get("planned_specs", [])
if not planned:
    raise SystemExit("missing planned_specs")

flagged = [item for item in planned if item.get("quality_flags")]
if not flagged:
    raise SystemExit("expected at least one quality flag in smoke fixture")

print("Plan quality:", quality.get("decision"), quality.get("recommendation"))
print("Planned specs:", len(planned))
print("Flagged specs:", ", ".join(item.get("planned_spec_id", "?") for item in flagged))
PY

echo
echo "Generated plan:"
echo "$WORKSPACE/.specify/sync/spec_build_plan.md"
