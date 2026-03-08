#!/bin/bash
# export-csv.sh - Export findings to CSV format

set -e

FINDINGS_FILE="${1:-findings.json}"
OUTPUT_FILE="${2:-findings.csv}"

if [ ! -f "$FINDINGS_FILE" ]; then
    echo "Findings file not found: $FINDINGS_FILE"
    exit 1
fi

echo "Exporting findings to CSV: $OUTPUT_FILE"

python3 << EOF
import json
import csv
import sys

try:
    with open("$FINDINGS_FILE") as f:
        data = json.load(f)
    
    with open("$OUTPUT_FILE", 'w', newline='') as csvfile:
        fieldnames = [
            'resource_id', 'resource_type', 'region', 'reason',
            'monthly_cost_usd', 'monthly_cost_inr', 'detected_at'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for finding in data.get('findings', []):
            writer.writerow({
                'resource_id': finding.get('resource_id'),
                'resource_type': finding.get('resource_type'),
                'region': finding.get('region'),
                'reason': finding.get('reason'),
                'monthly_cost_usd': finding.get('monthly_cost_usd'),
                'monthly_cost_inr': finding.get('monthly_cost_inr'),
                'detected_at': finding.get('detected_at')
            })
    
    print(f"Exported {len(data.get('findings', []))} findings to {OUTPUT_FILE}")
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
EOF
