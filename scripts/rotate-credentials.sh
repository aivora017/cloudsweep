#!/usr/bin/env bash
##############################################################################
# rotate-credentials.sh
#
# Rotates the CloudSweep PostgreSQL password without downtime:
#   1. Generate a new password
#   2. Update the DB user password (ALTER USER)
#   3. Patch the Kubernetes Secret
#   4. Restart the scanner CronJob pods so they pick up the new secret
#   5. Verify connectivity
#
# Usage:
#   ./scripts/rotate-credentials.sh [--namespace cloudsweep] [--kubeconfig ~/.kube/config]
##############################################################################

set -euo pipefail

NAMESPACE="cloudsweep"
KUBECONFIG_FILE="${HOME}/.kube/config"
SECRET_NAME="cloudsweep-secret"
POSTGRES_USER="cloudsweep"
POSTGRES_DB="cloudsweep"
POSTGRES_HOST="cloudsweep-postgres"
POSTGRES_PORT="5432"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --namespace)  NAMESPACE="$2";       shift 2 ;;
    --kubeconfig) KUBECONFIG_FILE="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

export KUBECONFIG="${KUBECONFIG_FILE}"

echo ""
echo "========================================"
echo "  CloudSweep credential rotation"
echo "  namespace : ${NAMESPACE}"
echo "========================================"
echo ""

# ---------------------------------------------------------------------------
# Step 1: Generate new password (32-char alphanumeric)
# ---------------------------------------------------------------------------
NEW_PASSWORD=$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 32)
echo "[1/5] New password generated (not shown)"

# ---------------------------------------------------------------------------
# Step 2: Alter PostgreSQL user password
# ---------------------------------------------------------------------------
echo "[2/5] Updating PostgreSQL password..."

POSTGRES_POD=$(kubectl get pods -n "${NAMESPACE}" \
  -l app=cloudsweep-postgres \
  --field-selector=status.phase=Running \
  -o jsonpath='{.items[0].metadata.name}')

kubectl exec -n "${NAMESPACE}" "${POSTGRES_POD}" -- \
  psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
  -c "ALTER USER ${POSTGRES_USER} WITH PASSWORD '${NEW_PASSWORD}';"

echo "  Password updated in PostgreSQL."

# ---------------------------------------------------------------------------
# Step 3: Build new DATABASE_URL and patch Secret
# ---------------------------------------------------------------------------
echo "[3/5] Patching Kubernetes Secret '${SECRET_NAME}'..."

NEW_DATABASE_URL="postgresql://${POSTGRES_USER}:${NEW_PASSWORD}@${POSTGRES_HOST}.${NAMESPACE}.svc.cluster.local:${POSTGRES_PORT}/${POSTGRES_DB}"

NEW_PG_PASS_B64=$(echo -n "${NEW_PASSWORD}" | base64 -w 0)
NEW_DATABASE_URL_B64=$(echo -n "${NEW_DATABASE_URL}" | base64 -w 0)

kubectl patch secret "${SECRET_NAME}" -n "${NAMESPACE}" \
  --type='json' \
  -p="[
    {\"op\": \"replace\", \"path\": \"/data/postgres-password\", \"value\": \"${NEW_PG_PASS_B64}\"},
    {\"op\": \"replace\", \"path\": \"/data/database-url\",      \"value\": \"${NEW_DATABASE_URL_B64}\"}
  ]"

echo "  Secret patched."

# ---------------------------------------------------------------------------
# Step 4: Restart scanner (delete running/pending pods so they re-read secret)
# ---------------------------------------------------------------------------
echo "[4/5] Restarting scanner pods to pick up new secret..."

kubectl delete pods -n "${NAMESPACE}" \
  -l "app.kubernetes.io/component=scanner" \
  --ignore-not-found=true

echo "  Scanner pods restarted."

# ---------------------------------------------------------------------------
# Step 5: Verify connectivity with new password
# ---------------------------------------------------------------------------
echo "[5/5] Verifying database connectivity..."

kubectl exec -n "${NAMESPACE}" "${POSTGRES_POD}" -- \
  psql "postgresql://${POSTGRES_USER}:${NEW_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}" \
  -c "SELECT COUNT(*) FROM scan_runs;" > /dev/null

echo "  Connection verified."

echo ""
echo "========================================"
echo "  Rotation complete!"
echo "  New password is live in:"
echo "    - PostgreSQL user '${POSTGRES_USER}'"
echo "    - Kubernetes Secret '${SECRET_NAME}' (namespace: ${NAMESPACE})"
echo "========================================"
echo ""
echo "  If GitHub Actions / Jenkins use DATABASE_URL, update those secrets too:"
echo "    gh secret set DATABASE_URL --body \"${NEW_DATABASE_URL}\""
