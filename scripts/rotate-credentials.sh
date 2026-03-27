#!/usr/bin/env bash
# rotate-credentials.sh
# Rotates the PostgreSQL password and patches the Kubernetes Secret in-place.
# Usage: ./scripts/rotate-credentials.sh [--namespace cloudsweep]

set -euo pipefail

NAMESPACE="cloudsweep"
SECRET_NAME="cloudsweep-secret"
POSTGRES_USER="cloudsweep"
POSTGRES_DB="cloudsweep"
POSTGRES_HOST="cloudsweep-postgres"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --namespace) NAMESPACE="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

NEW_PASSWORD=$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 32)

POSTGRES_POD=$(kubectl get pods -n "${NAMESPACE}" \
  -l app=cloudsweep-postgres \
  --field-selector=status.phase=Running \
  -o jsonpath='{.items[0].metadata.name}')

echo "Updating PostgreSQL password..."
kubectl exec -n "${NAMESPACE}" "${POSTGRES_POD}" -- \
  psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
  -c "ALTER USER ${POSTGRES_USER} WITH PASSWORD '${NEW_PASSWORD}';"

echo "Patching Kubernetes Secret..."
NEW_DATABASE_URL="postgresql://${POSTGRES_USER}:${NEW_PASSWORD}@${POSTGRES_HOST}.${NAMESPACE}.svc.cluster.local:5432/${POSTGRES_DB}"
kubectl patch secret "${SECRET_NAME}" -n "${NAMESPACE}" \
  --type='json' \
  -p="[
    {\"op\": \"replace\", \"path\": \"/data/postgres-password\", \"value\": \"$(echo -n "${NEW_PASSWORD}" | base64 -w 0)\"},
    {\"op\": \"replace\", \"path\": \"/data/database-url\",      \"value\": \"$(echo -n "${NEW_DATABASE_URL}" | base64 -w 0)\"}
  ]"

echo "Restarting scanner pods..."
kubectl delete pods -n "${NAMESPACE}" -l "app.kubernetes.io/component=scanner" --ignore-not-found=true

echo "Verifying connection..."
kubectl exec -n "${NAMESPACE}" "${POSTGRES_POD}" -- \
  psql "postgresql://${POSTGRES_USER}:${NEW_PASSWORD}@localhost:5432/${POSTGRES_DB}" \
  -c "SELECT COUNT(*) FROM scan_runs;" > /dev/null

echo "Done. Password rotated successfully."
echo ""
echo "If GitHub Actions / Jenkins use DATABASE_URL, update those secrets too:"
echo "  gh secret set DATABASE_URL --body \"${NEW_DATABASE_URL}\""
