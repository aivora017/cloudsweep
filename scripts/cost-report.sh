#!/usr/bin/env bash
##############################################################################
# cost-report.sh
#
# Generates a weekly CSV waste report from the PostgreSQL waste_trend_12w view.
# Output is saved to docs/reports/ and printed to stdout.
#
# Usage:
#   ./scripts/cost-report.sh [--namespace cloudsweep] [--weeks 4] [--output docs/reports/]
##############################################################################

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAMESPACE="cloudsweep"
WEEKS=12
OUTPUT_DIR="${REPO_ROOT}/docs/reports"
POSTGRES_USER="cloudsweep"
POSTGRES_DB="cloudsweep"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --namespace) NAMESPACE="$2";   shift 2 ;;
    --weeks)     WEEKS="$2";       shift 2 ;;
    --output)    OUTPUT_DIR="$2";  shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

mkdir -p "${OUTPUT_DIR}"
TIMESTAMP=$(date -u +%Y%m%d-%H%M%S)
CSV_FILE="${OUTPUT_DIR}/waste-report-${TIMESTAMP}.csv"

POSTGRES_POD=$(kubectl get pods -n "${NAMESPACE}" \
  -l app=cloudsweep-postgres \
  --field-selector=status.phase=Running \
  -o jsonpath='{.items[0].metadata.name}')

echo "Generating waste report from last ${WEEKS} weeks..."
echo ""

# Write CSV header
echo "scan_date,resource_type,finding_count,total_waste_inr,total_waste_usd" > "${CSV_FILE}"

# Query waste_trend view and append rows
kubectl exec -n "${NAMESPACE}" "${POSTGRES_POD}" -- \
  psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
  --csv -t \
  -c "
    SELECT
      scan_date,
      resource_type,
      finding_count,
      ROUND(total_waste_inr::numeric, 2) AS total_waste_inr,
      ROUND(total_waste_usd::numeric, 2) AS total_waste_usd
    FROM waste_trend_12w
    WHERE scan_date >= CURRENT_DATE - INTERVAL '${WEEKS} weeks'
    ORDER BY scan_date DESC, total_waste_inr DESC;
  " >> "${CSV_FILE}"

ROW_COUNT=$(tail -n +2 "${CSV_FILE}" | wc -l | tr -d ' ')

echo "Weekly summary (top 10 by waste):"
echo "----------------------------------------------"
kubectl exec -n "${NAMESPACE}" "${POSTGRES_POD}" -- \
  psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
  -c "
    SELECT
      TO_CHAR(scan_date, 'YYYY-MM-DD') AS date,
      resource_type AS type,
      finding_count AS count,
      '₹' || ROUND(total_waste_inr::numeric, 0)::text AS inr_per_month
    FROM waste_trend_12w
    WHERE scan_date >= CURRENT_DATE - INTERVAL '${WEEKS} weeks'
    ORDER BY scan_date DESC, total_waste_inr DESC
    LIMIT 10;
  "

echo ""
echo "All-time total (unresolved):"
kubectl exec -n "${NAMESPACE}" "${POSTGRES_POD}" -- \
  psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
  -c "
    SELECT
      resource_type,
      COUNT(*) AS findings,
      '₹' || ROUND(SUM(monthly_cost_inr)::numeric, 0)::text AS monthly_waste_inr
    FROM findings
    WHERE resolved_at IS NULL
    GROUP BY resource_type
    ORDER BY SUM(monthly_cost_inr) DESC;
  "

echo ""
echo "Report saved: ${CSV_FILE}  (${ROW_COUNT} rows)"
