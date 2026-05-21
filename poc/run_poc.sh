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


echo "== downstream_context_guard =="
guard_workspace="$OUT/downstream_context_guard"
rm -rf "$guard_workspace"
mkdir -p "$guard_workspace/.specify/memory" "$guard_workspace/.specify/sync" "$guard_workspace/specs/001-demo"

cat > "$guard_workspace/HLD.md" <<'EOF'
# HLD

## HLD-001 - Demo

HLD-ID: HLD-001
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: 001
HLD-RESOURCES: TBD
HLD-VERIFY: downstream context guard can target this section

Demo body.
EOF

printf '# Constitution\n' > "$guard_workspace/.specify/memory/constitution.md"
printf '{"specs":[]}\n' > "$guard_workspace/.specify/sync/spec_index.json"
printf '# Demo Spec\n' > "$guard_workspace/specs/001-demo/spec.md"

set +e
python3 "$ROOT/hld_spec_downstream.py" \
  --workspace "$guard_workspace" \
  --hld "$guard_workspace/HLD.md" \
  --phase analyze \
  --prompt-only \
  --agent codex \
  >"$guard_workspace/unbounded.out" 2>&1
guard_rc=$?
set -e

if [ "$guard_rc" -eq 0 ]; then
  echo "ERROR: unbounded downstream prompt unexpectedly passed"
  cat "$guard_workspace/unbounded.out"
  exit 1
fi

grep -q "Refusing to build an unbounded downstream prompt" "$guard_workspace/unbounded.out"
echo "Unbounded downstream prompt: blocked"

python3 "$ROOT/hld_spec_downstream.py" \
  --workspace "$guard_workspace" \
  --hld "$guard_workspace/HLD.md" \
  --phase analyze \
  --prompt-only \
  --agent codex \
  --max-hld-chars 30000 \
  >"$guard_workspace/bounded_chars.out" 2>&1

grep -q "Prompt-only mode" "$guard_workspace/bounded_chars.out"
echo "Explicit char-bound downstream prompt: passed"

python3 "$ROOT/hld_spec_downstream.py" \
  --workspace "$guard_workspace" \
  --hld "$guard_workspace/HLD.md" \
  --use-hld-map \
  --target-hld HLD-001 \
  --phase analyze \
  --prompt-only \
  --agent codex \
  >"$guard_workspace/bounded_map.out" 2>&1

grep -q "HLD map: True" "$guard_workspace/bounded_map.out"
echo "HLD-map bounded downstream prompt: passed"
echo

echo "Done."
