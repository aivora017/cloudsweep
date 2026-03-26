#!/usr/bin/env bash
##############################################################################
# bulk-resolve.sh
#
# Marks all currently active findings as resolved after a cleanup sprint.
# Optionally filters by resource type or region.
#
# Usage:
#   ./scripts/bulk-resolve.sh                             # resolve everything
#   ./scripts/bulk-resolve.sh --type EC2                  # resolve EC2 only
#   ./scripts/bulk-resolve.sh --region us-east-1          # resolve one region
#   ./scripts/bulk-resolve.sh --type EBS --dry-run        # preview only
##############################################################################

set -euo pipefail

NAMESPACE="cloudsweep"
RESOURCE_TYPE=""
REGION_FILTER=""
DRY_RUN=false
POSTGRES_USER="cloudsweep"
POSTGRES_DB="cloudsweep"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --type)       RESOURCE_TYPE="$2"; shift 2 ;;
    --region)     REGION_FILTER="$2"; shift 2 ;;
    --namespace)  NAMESPACE="$2";     shift 2 ;;
    --dry-run)    DRY_RUN=true;       shift ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

echo ""
echo "============================================"
echo "  CloudSweep bulk-resolve"
echo "  type   : ${RESOURCE_TYPE:-ALL}"
echo "  region : ${REGION_FILTER:-ALL}"
echo "  dry-run: ${DRY_RUN}"
echo "============================================"
echo ""

# Build WHERE clause
WHERE="resolved_at IS NULL"
[[ -n "${RESOURCE_TYPE}" ]] && WHERE="${WHERE} AND resource_type = '${RESOURCE_TYPE}'"
[[ -n "${REGION_FILTER}" ]] && WHERE="${WHERE} AND region = '${REGION_FILTER}'"

POSTGRES_POD=$(kubectl get pods -n "${NAMESPACE}" \
  -l app=cloudsweep-postgres \
  --field-selector=status.phase=Running \
  -o jsonpath='{.items[0].metadata.name}')

# Preview count
COUNT=$(kubectl exec -n "${NAMESPACE}" "${POSTGRES_POD}" -- \
  psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -t \
  -c "SELECT COUNT(*) FROM findings WHERE ${WHERE};")
COUNT=$(echo "${COUNT}" | tr -d ' ')

echo "  Findings to resolve: ${COUNT}"

if [[ "${DRY_RUN}" == "true" ]]; then
  echo ""
  echo "  DRY-RUN: no changes made."
  echo "  Run without --dry-run to apply."
  exit 0
fi

if [[ "${COUNT}" -eq 0 ]]; then
  echo "  Nothing to resolve."
  exit 0
fi

read -r -p "  Resolve ${COUNT} findings? [y/N] " confirm
if [[ "${confirm}" != "y" && "${confirm}" != "Y" ]]; then
  echo "  Aborted."
  exit 0
fi

# Apply
kubectl exec -n "${NAMESPACE}" "${POSTGRES_POD}" -- \
  psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
  -c "UPDATE findings SET resolved_at = NOW(), updated_at = NOW() WHERE ${WHERE};"

echo ""
echo "  ${COUNT} finding(s) marked as resolved."
echo ""
echo "  To verify:"
echo "    kubectl exec -n ${NAMESPACE} ${POSTGRES_POD} -- \\"
echo "      psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} \\"
echo "      -c 'SELECT resource_type, COUNT(*) FROM findings WHERE resolved_at IS NOT NULL GROUP BY 1;'"
