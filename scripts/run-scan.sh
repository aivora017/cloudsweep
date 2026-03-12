#!/usr/bin/env bash
set -euo pipefail

REGIONS="${1:-ap-south-1}"

python -m scanner.main --dry-run --regions "${REGIONS}" --output findings.json

echo "Scan complete. Output written to findings.json"
