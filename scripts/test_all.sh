#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${1:-}" == "--local" ]]; then
  shift
  exec python3 "$SCRIPT_DIR/test_local.py" "$@"
fi
if [[ $# -ne 0 ]]; then
  echo "FAIL: usage: scripts/test_all.sh [--local]" >&2
  exit 1
fi
for test in ping backends dns https load_balancing caching; do
  echo "Checking $test"
  if ! "$SCRIPT_DIR/test_${test}.sh"; then
    echo "FAIL: stopped at $test; diagnose and fix before continuing" >&2
    exit 1
  fi
done
echo "PASS: all Phase 1 checks on this laptop; run on the other laptop too"
