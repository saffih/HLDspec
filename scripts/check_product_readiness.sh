#!/usr/bin/env bash
# Reproducible local product-readiness check for HLDspec.
#
# Runs syntax checks, the focused readiness/operator/anti-drift/terminology and
# product-readiness/repo-layout tests, the full tests_v2 suite, the deterministic
# smoke, and a working-tree whitespace check. It is local-only and does not
# replace CI or a release process. See docs/PRODUCT_READINESS.md.
#
# Usage:
#   scripts/check_product_readiness.sh
#
# Exit code: 0 only if every step passes; non-zero on the first failure.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PYTHONPYCACHEPREFIX="$ROOT/.tmp/pycache"
mkdir -p "$ROOT/.tmp/pycache"

step() { printf '\n=== %s ===\n' "$1"; }

step "bash -n on shell scripts"
bash -n scripts/check_product_readiness.sh

step "py_compile on key Python files"
python3 -m py_compile \
  hldspec/speckit_operator_state.py \
  hldspec/speckit_readiness.py \
  scripts/hldspec_agent_session.py \
  tests_v2/test_speckit_operator_state.py \
  tests_v2/test_product_readiness_docs.py \
  tests_v2/test_repo_layout_readability.py \
  tests_v2/test_agent_first_user_interface.py \
  tests_v2/test_architecture_layers_contract.py \
  tests_v2/test_repo_top_level_classification.py \
  tests_v2/test_product_readiness_script.py

step "focused tests: Operator State"
python3 -m unittest tests_v2.test_speckit_operator_state

step "focused tests: SpecKit readiness"
python3 -m unittest tests_v2.test_speckit_readiness

step "focused tests: anti-drift contracts"
python3 -m unittest tests_v2.test_anti_drift_contracts

step "focused tests: terminology and flow docs"
python3 -m unittest tests_v2.test_terminology_and_flow_docs

step "focused tests: product readiness docs"
python3 -m unittest tests_v2.test_product_readiness_docs

step "focused tests: repo layout readability"
python3 -m unittest tests_v2.test_repo_layout_readability

step "focused tests: agent-first user interface"
python3 -m unittest tests_v2.test_agent_first_user_interface

step "focused tests: architecture layers contract"
python3 -m unittest tests_v2.test_architecture_layers_contract

step "focused tests: top-level classification"
python3 -m unittest tests_v2.test_repo_top_level_classification

step "full suite: tests_v2"
python3 -m unittest discover -s tests_v2

step "deterministic smoke"
python3 scripts/hldspec_smoke_slice_e2e.py --json

step "working-tree whitespace check"
git diff --check

printf '\nPRODUCT_READINESS_CHECK: PASS\n'
