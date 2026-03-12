#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${SLACK_WEBHOOK_URL:-}" ]]; then
  echo "SLACK_WEBHOOK_URL is required"
  exit 1
fi

python scripts/test-findings-slack.py

echo "Slack digest test sent"
