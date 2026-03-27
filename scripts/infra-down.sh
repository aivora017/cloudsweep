#!/usr/bin/env bash
# infra-down.sh
# Tears down all CloudSweep infrastructure (Helm uninstall + terraform destroy).
# Usage: ./scripts/infra-down.sh --gcp-project <project> [--env dev|prod] [--auto-approve]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="${REPO_ROOT}/infra/terraform"

ENV="dev"
GCP_PROJECT=""
AWS_REGION="ap-south-1"
KEY_NAME=""
AUTO_APPROVE=""
KUBECONFIG_FILE="${REPO_ROOT}/kubeconfig-cloudsweep_server.yaml"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)          ENV="$2";          shift 2 ;;
    --gcp-project)  GCP_PROJECT="$2";  shift 2 ;;
    --aws-region)   AWS_REGION="$2";   shift 2 ;;
    --key-name)     KEY_NAME="$2";     shift 2 ;;
    --auto-approve) AUTO_APPROVE="-auto-approve"; shift ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

if [[ -z "${GCP_PROJECT}" ]]; then
  echo "ERROR: --gcp-project is required"
  exit 1
fi

echo "infra-down  env=${ENV}  region=${AWS_REGION}"
echo ""

echo "[1/2] Uninstalling Helm charts..."

if [[ -f "${KUBECONFIG_FILE}" ]]; then
  export KUBECONFIG="${KUBECONFIG_FILE}"
fi

# Uninstall CloudSweep
helm uninstall cloudsweep --namespace cloudsweep 2>/dev/null && echo "  cloudsweep uninstalled" || echo "  cloudsweep not found, skipping"

# Remove monitoring manifests
kubectl delete -f "${REPO_ROOT}/infra/k8s/prometheusrule.yaml"  2>/dev/null || true
kubectl delete -f "${REPO_ROOT}/infra/k8s/grafana-dashboards-configmap.yaml" 2>/dev/null || true
kubectl delete -f "${REPO_ROOT}/infra/k8s/pushgateway.yaml" 2>/dev/null || true

helm uninstall kube-prometheus-stack --namespace monitoring 2>/dev/null && echo "  kube-prometheus-stack uninstalled" || echo "  kube-prometheus-stack not found, skipping"

echo "[2/2] Terraform destroy..."

TF_VARS=(
  -var="env=${ENV}"
  -var="aws_region=${AWS_REGION}"
  -var="gcp_project=${GCP_PROJECT}"
  -var="key_name=${KEY_NAME:-placeholder}"
)

terraform -chdir="${TF_DIR}" destroy ${AUTO_APPROVE} "${TF_VARS[@]}"

echo ""
echo "Done. All infrastructure destroyed."
