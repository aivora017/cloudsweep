#!/usr/bin/env bash
# infra-up.sh
# Provisions the full CloudSweep infrastructure: Terraform, Ansible, Helm.
# Usage: ./scripts/infra-up.sh --key-name <keypair> --gcp-project <project> [--env dev|prod]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="${REPO_ROOT}/infra/terraform"
ANSIBLE_DIR="${REPO_ROOT}/infra/ansible"

ENV="dev"
KEY_FILE="${HOME}/.ssh/id_rsa"
KEY_NAME=""
GCP_PROJECT=""
AWS_REGION="ap-south-1"
INSTANCE_TYPE="t2.micro"
TF_BACKEND_BUCKET=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)           ENV="$2";             shift 2 ;;
    --key-file)      KEY_FILE="$2";        shift 2 ;;
    --key-name)      KEY_NAME="$2";        shift 2 ;;
    --gcp-project)   GCP_PROJECT="$2";     shift 2 ;;
    --aws-region)    AWS_REGION="$2";      shift 2 ;;
    --instance-type) INSTANCE_TYPE="$2";   shift 2 ;;
    --tf-bucket)     TF_BACKEND_BUCKET="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

if [[ -z "${KEY_NAME}" ]]; then
  echo "ERROR: --key-name is required (name of your AWS EC2 key pair)"
  exit 1
fi
if [[ -z "${GCP_PROJECT}" ]]; then
  echo "ERROR: --gcp-project is required"
  exit 1
fi
if [[ ! -f "${KEY_FILE}" ]]; then
  echo "ERROR: key file not found: ${KEY_FILE}"
  exit 1
fi

echo "infra-up  env=${ENV}  region=${AWS_REGION}  instance=${INSTANCE_TYPE}  key=${KEY_NAME}  gcp=${GCP_PROJECT}"
echo ""

echo "[1/4] Terraform apply..."

TF_INIT_ARGS=""
if [[ -n "${TF_BACKEND_BUCKET}" ]]; then
  TF_INIT_ARGS="-backend-config=bucket=${TF_BACKEND_BUCKET}"
fi

terraform -chdir="${TF_DIR}" init -input=false ${TF_INIT_ARGS}

terraform -chdir="${TF_DIR}" apply -auto-approve \
  -var="env=${ENV}" \
  -var="aws_region=${AWS_REGION}" \
  -var="key_name=${KEY_NAME}" \
  -var="instance_type=${INSTANCE_TYPE}" \
  -var="gcp_project=${GCP_PROJECT}"

SERVER_IP=$(terraform -chdir="${TF_DIR}" output -raw server_ip)
IAM_ROLE_ARN=$(terraform -chdir="${TF_DIR}" output -raw iam_role_arn)
REPORTS_BUCKET=$(terraform -chdir="${TF_DIR}" output -raw reports_bucket)

echo ""
echo "  server_ip      : ${SERVER_IP}"
echo "  iam_role_arn   : ${IAM_ROLE_ARN}"
echo "  reports_bucket : ${REPORTS_BUCKET}"
echo ""

echo "[2/4] Waiting for SSH on ${SERVER_IP}:22..."

SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10"
MAX_TRIES=30
TRIES=0

until ssh ${SSH_OPTS} -i "${KEY_FILE}" "ec2-user@${SERVER_IP}" "echo ok" &>/dev/null; do
  TRIES=$((TRIES + 1))
  if [[ ${TRIES} -ge ${MAX_TRIES} ]]; then
    echo "ERROR: SSH not available after $((MAX_TRIES * 10)) seconds"
    exit 1
  fi
  echo "  waiting... (${TRIES}/${MAX_TRIES})"
  sleep 10
done
echo "  SSH is up."

echo "[3/4] Running Ansible playbook..."

ansible-playbook \
  -i "${ANSIBLE_DIR}/inventory.sh" \
  "${ANSIBLE_DIR}/site.yml" \
  --private-key "${KEY_FILE}" \
  -e "ansible_ssh_private_key_file=${KEY_FILE}"

# Fetch kubeconfig
KUBECONFIG_FILE="${REPO_ROOT}/kubeconfig-cloudsweep_server.yaml"
if [[ -f "${KUBECONFIG_FILE}" ]]; then
  export KUBECONFIG="${KUBECONFIG_FILE}"
  echo "  KUBECONFIG set to ${KUBECONFIG_FILE}"
fi

echo "[4/4] Deploying Helm charts..."

# Ensure repos are present
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || true
helm repo add grafana https://grafana.github.io/helm-charts 2>/dev/null || true
helm repo update

# CloudSweep namespace
kubectl create namespace cloudsweep --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace monitoring  --dry-run=client -o yaml | kubectl apply -f -

# kube-prometheus-stack (Prometheus + Grafana + Alertmanager)
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  -f "${REPO_ROOT}/helm/kube-prometheus-stack-values.yaml" \
  --timeout 5m

# Pushgateway + dashboards + alert rules
kubectl apply -f "${REPO_ROOT}/infra/k8s/pushgateway.yaml"
kubectl apply -f "${REPO_ROOT}/infra/k8s/grafana-dashboards-configmap.yaml"
kubectl apply -f "${REPO_ROOT}/infra/k8s/prometheusrule.yaml"

# CloudSweep chart
helm upgrade --install cloudsweep "${REPO_ROOT}/helm/cloudsweep" \
  --namespace cloudsweep \
  --set aws.region="${AWS_REGION}" \
  --set monitoring.pushgateway.url="http://pushgateway.cloudsweep.svc.cluster.local:9091" \
  --timeout 5m

echo ""
echo "Done. CloudSweep is running."
echo "  Server IP  : ${SERVER_IP}"
echo "  IAM role   : ${IAM_ROLE_ARN}"
echo "  S3 bucket  : ${REPORTS_BUCKET}"
echo ""
echo "  Grafana:  kubectl port-forward svc/kube-prometheus-stack-grafana 3000:80 -n monitoring"
echo "  Jenkins:  http://${SERVER_IP}:8081"
