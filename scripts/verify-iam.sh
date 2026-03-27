#!/usr/bin/env bash
# verify-iam.sh
# Confirms the scanner IAM role is read-only using simulate-principal-policy.
# Usage: ./scripts/verify-iam.sh --role-arn <arn>
#        ./scripts/verify-iam.sh   (auto-detects from terraform output)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROLE_ARN=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --role-arn) ROLE_ARN="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

if [[ -z "${ROLE_ARN}" ]]; then
  TF_DIR="${REPO_ROOT}/infra/terraform"
  if command -v terraform &>/dev/null && [[ -d "${TF_DIR}/.terraform" ]]; then
    ROLE_ARN=$(terraform -chdir="${TF_DIR}" output -raw iam_role_arn 2>/dev/null || true)
  fi
fi

if [[ -z "${ROLE_ARN}" ]]; then
  echo "ERROR: --role-arn required (or run terraform apply first)"
  exit 1
fi

echo "Simulating policy for: ${ROLE_ARN}"
echo ""

PASS=0
FAIL=0

simulate() {
  local label="$1"
  local action="$2"
  local expected="$3"

  result=$(aws iam simulate-principal-policy \
    --policy-source-arn "${ROLE_ARN}" \
    --action-names "${action}" \
    --resource-arns "*" \
    --query 'EvaluationResults[0].EvalDecision' \
    --output text 2>/dev/null)

  if [[ "${result}" == "${expected}" ]]; then
    printf "  PASS  %-45s  %s\n" "${label}" "${result}"
    PASS=$((PASS + 1))
  else
    printf "  FAIL  %-45s  got=%s expected=%s\n" "${label}" "${result}" "${expected}"
    FAIL=$((FAIL + 1))
  fi
}

echo "Read actions (must be allowed):"
simulate "ec2:DescribeInstances"                           "ec2:DescribeInstances"                       "allowed"
simulate "ec2:DescribeVolumes"                             "ec2:DescribeVolumes"                         "allowed"
simulate "ec2:DescribeSnapshots"                           "ec2:DescribeSnapshots"                       "allowed"
simulate "ec2:DescribeAddresses"                           "ec2:DescribeAddresses"                       "allowed"
simulate "cloudwatch:GetMetricStatistics"                  "cloudwatch:GetMetricStatistics"              "allowed"
simulate "cloudwatch:ListMetrics"                          "cloudwatch:ListMetrics"                      "allowed"
simulate "ce:GetCostAndUsage"                              "ce:GetCostAndUsage"                          "allowed"
simulate "ce:GetRightsizingRecommendation"                 "ce:GetRightsizingRecommendation"             "allowed"
simulate "rds:DescribeDBInstances"                         "rds:DescribeDBInstances"                     "allowed"
simulate "elasticloadbalancing:DescribeLoadBalancers"      "elasticloadbalancing:DescribeLoadBalancers"  "allowed"

echo ""
echo "Write actions (must be denied):"
simulate "ec2:TerminateInstances"   "ec2:TerminateInstances"   "implicitDeny"
simulate "ec2:DeleteVolume"         "ec2:DeleteVolume"         "implicitDeny"
simulate "ec2:DeleteSnapshot"       "ec2:DeleteSnapshot"       "implicitDeny"
simulate "ec2:RunInstances"         "ec2:RunInstances"         "implicitDeny"
simulate "rds:DeleteDBInstance"     "rds:DeleteDBInstance"     "implicitDeny"
simulate "s3:DeleteBucket"          "s3:DeleteBucket"          "implicitDeny"
simulate "iam:CreateUser"           "iam:CreateUser"           "implicitDeny"
simulate "cloudwatch:DeleteAlarms"  "cloudwatch:DeleteAlarms"  "implicitDeny"

echo ""
echo "Results: ${PASS} passed, ${FAIL} failed"

if [[ "${FAIL}" -gt 0 ]]; then
  echo "FAIL: some actions did not match expected policy decision"
  exit 1
fi

echo "PASS: scanner role is read-only"
