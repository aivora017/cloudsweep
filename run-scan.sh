#!/bin/bash
# run-scan.sh - Execute CloudSweep scanner and store findings

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FINDINGS_FILE="${SCRIPT_DIR}/findings.json"

echo "CloudSweep Scanner - $(date '+%Y-%m-%d %H:%M:%S IST')"
echo "=================================================="

# Load environment variables if .env exists
if [ -f "${SCRIPT_DIR}/.env" ]; then
    export $(cat "${SCRIPT_DIR}/.env" | xargs)
fi

# Run the scanner
python -m scanner.main \
    --regions "${AWS_REGIONS:-ap-south-1,us-east-1}" \
    --output "${FINDINGS_FILE}"

echo ""
echo "Scan complete"
echo "Findings saved to: ${FINDINGS_FILE}"

# Display summary
if [ -f "${FINDINGS_FILE}" ]; then
    echo ""
    python3 << 'EOF'
import json
import sys

try:
    with open(sys.argv[1]) as f:
        data = json.load(f)
        summary = data.get('summary', {})
        print(f"Total Findings: {summary.get('total_findings', 0)}")
        print(f"Total Waste: ₹{summary.get('total_waste_inr', 0):,.2f}")
        print(f"Regions: {', '.join(summary.get('regions_scanned', []))}")
except Exception as e:
    print(f"Error reading findings: {e}", file=sys.stderr)
EOF
    "${FINDINGS_FILE}"
fi
