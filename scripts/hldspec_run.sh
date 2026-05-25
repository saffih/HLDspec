#!/usr/bin/env bash
# Canonical HLDspec entry point.
# Runs preflight safety checks, then delegates to project_continue.sh.
#
# Usage: scripts/hldspec_run.sh [args...]
# Skip preflight: HLDSPEC_SKIP_PREFLIGHT=1 scripts/hldspec_run.sh [args...]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ "${HLDSPEC_SKIP_PREFLIGHT:-0}" != "1" ]; then
  if command -v python3 &>/dev/null; then
    python3 "$ROOT/scripts/preflight_check.py" --repo "$ROOT" --fail-on-unsafe || {
      echo "HLDspec preflight check failed. Fix the issues above before running." >&2
      exit 2
    }
  fi
fi

exec "$ROOT/scripts/project_continue.sh" "$@"
