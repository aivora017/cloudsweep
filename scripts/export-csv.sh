#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required"
  exit 1
fi

OUT_FILE="${1:-findings_export.csv}"
export OUT_FILE

python - <<'PY'
import csv
import os
import psycopg2

out_file = os.environ.get("OUT_FILE", "findings_export.csv")
dsn = os.environ["DATABASE_URL"]

conn = psycopg2.connect(dsn)
cur = conn.cursor()
cur.execute(
    """
    SELECT resource_id, resource_type, region, reason, monthly_cost_usd, monthly_cost_inr, detected_at, resolved_at
    FROM findings
    ORDER BY detected_at DESC
    """
)
rows = cur.fetchall()

with open(out_file, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "resource_id",
        "resource_type",
        "region",
        "reason",
        "monthly_cost_usd",
        "monthly_cost_inr",
        "detected_at",
        "resolved_at",
    ])
    writer.writerows(rows)

cur.close()
conn.close()
print(f"Exported {len(rows)} rows to {out_file}")
PY
