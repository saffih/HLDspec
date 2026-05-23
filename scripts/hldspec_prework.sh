#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  hldspec_prework.sh <path-to-HLD.md> [workspace] [--force]

Builds read-only HLDspec prework artifacts:
- HLD format/reporting
- HLD map
- section classification
- use-case/API map
- spec build plan
- quality review
- prework package
- state report

Does not invoke SpecKit and does not create specs.
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ] || [ "$#" -lt 1 ]; then
  usage
  exit 0
fi

exec bash "$ROOT/scripts/first_run_readonly.sh" "$@"
