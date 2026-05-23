#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

run_python() {
  if command -v uv >/dev/null 2>&1; then
    export UV_CACHE_DIR="${UV_CACHE_DIR:-$PWD/.hldspec-uv-cache}"
    uv run python "$@"
  else
    python3 "$@"
  fi
}

usage() {
  cat <<'EOF'
Usage:
  hldspec_agent_start.sh <source-HLD.md> [--workspace /path/to/workspace] [--force]

User-facing meaning:
  HLDspec /absolute/path/to/HLD.md

Generates an agent-start prompt/context for the HLDspec Orchestrator Agent.
It does not invoke SpecKit, create final specs, implement, or edit the source HLD.
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ] || [ "$#" -lt 1 ]; then
  usage
  exit 0
fi

SOURCE_HLD="$1"
shift

WORKSPACE=""
FORCE=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --workspace)
      if [ "$#" -lt 2 ] || [ -z "${2:-}" ]; then
        echo "ERROR: --workspace requires a path" >&2
        exit 2
      fi
      WORKSPACE="$2"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

ARGS=("$ROOT/scripts/build_hldspec_agent_start_prompt.py" "$SOURCE_HLD" --repo "$ROOT")
if [ -n "$WORKSPACE" ]; then
  ARGS+=(--workspace "$WORKSPACE")
fi
if [ "$FORCE" = "1" ]; then
  ARGS+=(--force)
fi

run_python "${ARGS[@]}"

if [ -n "$WORKSPACE" ]; then
  PROMPT="$WORKSPACE/.specify/sync/hldspec_agent_start_prompt.md"
else
  PROMPT="$(run_python - <<PY
from pathlib import Path
import re
source = Path("$SOURCE_HLD").expanduser()
text = re.sub(r"[^A-Za-z0-9_.-]+", "-", source.stem.strip()).strip("-._") or "hld"
print(Path("/tmp") / f"hldspec-agent-{text}" / ".specify" / "sync" / "hldspec_agent_start_prompt.md")
PY
)"
fi

echo
echo "Open this prompt with the HLDspec Orchestrator Agent:"
echo "$PROMPT"
echo

if [ -f "$PROMPT" ]; then
  cat "$PROMPT"
fi
