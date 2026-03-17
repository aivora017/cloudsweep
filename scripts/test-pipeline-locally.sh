#!/bin/bash
# Mimics Jenkins Lint and Test stages locally.
# Run from repo root: bash scripts/test-pipeline-locally.sh

set -euo pipefail

PASS=0
FAIL=0

run_stage() {
    local name="$1"
    shift
    echo ""
    echo "=== $name ==="
    if "$@"; then
        echo "PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name"
        FAIL=$((FAIL + 1))
    fi
}

# Lint stage
run_stage "flake8" flake8 scanner/ notifier/ db/
run_stage "bandit" bandit -r scanner/ notifier/ -ll

# Test stage
run_stage "pytest" pytest tests/ --cov=scanner --cov=notifier \
    --cov-report=term-missing --cov-fail-under=85

echo ""
echo "=============================="
echo "Results: $PASS passed, $FAIL failed"
echo "=============================="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
