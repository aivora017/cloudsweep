#!/usr/bin/env bash
##############################################################################
# seed-demo-waste.sh
#
# Creates demo AWS waste resources in ap-south-1 for CloudSweep proof-of-concept:
#   - 3 × t2.micro EC2 instances (idle — no workload, <5% CPU)
#   - 2 × 20 GB gp3 EBS volumes (unattached)
#   - 1 × Elastic IP (unassociated)
#
# Estimated monthly waste:  ~₹2,760 / ~$33
#   EC2 t2.micro × 3    $0.0116/hr → $8.35/mo × 3 = $25.06 ≈ ₹2,092
#   EBS gp3 20 GB × 2   $0.08/GB/mo × 20 = $1.60/mo × 2 = $3.20 ≈ ₹267
#   EIP unused           $0.005/hr → $3.60/mo ≈ ₹300
#
# Usage:
#   ./scripts/seed-demo-waste.sh [--region ap-south-1] [--key-name <keypair>]
#
# Cleanup (run after demo):
#   ./scripts/seed-demo-waste.sh --cleanup
##############################################################################

set -euo pipefail

REGION="ap-south-1"
KEY_NAME=""
AMI_ID=""
CLEANUP=false
STATE_FILE="/tmp/cloudsweep-demo-resources.json"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --region)   REGION="$2";   shift 2 ;;
    --key-name) KEY_NAME="$2"; shift 2 ;;
    --cleanup)  CLEANUP=true;  shift ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

# ---------------------------------------------------------------------------
# Cleanup mode
# ---------------------------------------------------------------------------
if [[ "${CLEANUP}" == "true" ]]; then
  if [[ ! -f "${STATE_FILE}" ]]; then
    echo "ERROR: state file not found: ${STATE_FILE}"
    echo "Cannot clean up — resource IDs are unknown."
    exit 1
  fi

  echo "Reading saved resource IDs from ${STATE_FILE}..."
  INSTANCE_IDS=$(jq -r '.instances[]' "${STATE_FILE}" | tr '\n' ' ')
  VOLUME_IDS=$(jq -r '.volumes[]' "${STATE_FILE}" | tr '\n' ' ')
  ALLOC_IDS=$(jq -r '.eip_allocations[]' "${STATE_FILE}" | tr '\n' ' ')

  echo "Terminating EC2 instances: ${INSTANCE_IDS}"
  aws ec2 terminate-instances --instance-ids ${INSTANCE_IDS} --region "${REGION}" > /dev/null

  echo "Waiting for instances to terminate..."
  aws ec2 wait instance-terminated --instance-ids ${INSTANCE_IDS} --region "${REGION}"

  echo "Deleting EBS volumes: ${VOLUME_IDS}"
  for vol in ${VOLUME_IDS}; do
    aws ec2 delete-volume --volume-id "${vol}" --region "${REGION}" && echo "  deleted ${vol}"
  done

  echo "Releasing EIPs: ${ALLOC_IDS}"
  for alloc in ${ALLOC_IDS}; do
    aws ec2 release-address --allocation-id "${alloc}" --region "${REGION}" && echo "  released ${alloc}"
  done

  rm -f "${STATE_FILE}"
  echo ""
  echo "Cleanup complete. All demo resources deleted."
  exit 0
fi

# ---------------------------------------------------------------------------
# Resolve AMI (Amazon Linux 2023, latest)
# ---------------------------------------------------------------------------
echo "Resolving latest Amazon Linux 2023 AMI in ${REGION}..."
AMI_ID=$(aws ec2 describe-images \
  --owners amazon \
  --filters \
    "Name=name,Values=al2023-ami-*-x86_64" \
    "Name=architecture,Values=x86_64" \
    "Name=virtualization-type,Values=hvm" \
  --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
  --output text \
  --region "${REGION}")

echo "  AMI: ${AMI_ID}"

# ---------------------------------------------------------------------------
# Launch 3 × t2.micro instances (no keypair = no SSH = truly ephemeral demo)
# ---------------------------------------------------------------------------
echo ""
echo "Launching 3 × t2.micro idle EC2 instances..."

LAUNCH_ARGS=(
  --image-id "${AMI_ID}"
  --instance-type t2.micro
  --count 3
  --no-associate-public-ip-address
  --tag-specifications
    "ResourceType=instance,Tags=[{Key=Name,Value=cloudsweep-demo-idle},{Key=Project,Value=cloudsweep},{Key=Demo,Value=true},{Key=Env,Value=demo}]"
  --region "${REGION}"
  --query 'Instances[*].InstanceId'
  --output text
)

if [[ -n "${KEY_NAME}" ]]; then
  LAUNCH_ARGS+=(--key-name "${KEY_NAME}")
fi

INSTANCE_IDS_RAW=$(aws ec2 run-instances "${LAUNCH_ARGS[@]}")
INSTANCE_IDS=($INSTANCE_IDS_RAW)

echo "  Launched: ${INSTANCE_IDS[*]}"
echo "  Waiting for instances to reach 'running' state..."
aws ec2 wait instance-running --instance-ids "${INSTANCE_IDS[@]}" --region "${REGION}"
echo "  All 3 instances running."

# ---------------------------------------------------------------------------
# Create 2 × 20 GB gp3 EBS volumes (unattached)
# ---------------------------------------------------------------------------
echo ""
echo "Creating 2 × 20 GB gp3 EBS volumes (unattached)..."

AZ=$(aws ec2 describe-subnets \
  --filters "Name=defaultForAz,Values=true" \
  --query 'Subnets[0].AvailabilityZone' \
  --output text \
  --region "${REGION}")

VOLUME_IDS=()
for i in 1 2; do
  VOL_ID=$(aws ec2 create-volume \
    --availability-zone "${AZ}" \
    --size 20 \
    --volume-type gp3 \
    --tag-specifications \
      "ResourceType=volume,Tags=[{Key=Name,Value=cloudsweep-demo-orphan-${i}},{Key=Project,Value=cloudsweep},{Key=Demo,Value=true}]" \
    --query 'VolumeId' \
    --output text \
    --region "${REGION}")
  VOLUME_IDS+=("${VOL_ID}")
  echo "  Created: ${VOL_ID}"
done

# ---------------------------------------------------------------------------
# Allocate 1 × unused EIP
# ---------------------------------------------------------------------------
echo ""
echo "Allocating 1 × unused Elastic IP..."

ALLOC_ID=$(aws ec2 allocate-address \
  --domain vpc \
  --tag-specifications \
    "ResourceType=elastic-ip,Tags=[{Key=Name,Value=cloudsweep-demo-unused-eip},{Key=Project,Value=cloudsweep},{Key=Demo,Value=true}]" \
  --query 'AllocationId' \
  --output text \
  --region "${REGION}")
EIP=$(aws ec2 describe-addresses \
  --allocation-ids "${ALLOC_ID}" \
  --query 'Addresses[0].PublicIp' \
  --output text \
  --region "${REGION}")

echo "  AllocationId: ${ALLOC_ID}  IP: ${EIP}"

# ---------------------------------------------------------------------------
# Save state for cleanup
# ---------------------------------------------------------------------------
cat > "${STATE_FILE}" <<EOF
{
  "region": "${REGION}",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "instances": $(printf '%s\n' "${INSTANCE_IDS[@]}" | jq -R . | jq -s .),
  "volumes": $(printf '%s\n' "${VOLUME_IDS[@]}" | jq -R . | jq -s .),
  "eip_allocations": ["${ALLOC_ID}"],
  "eip_public_ips": ["${EIP}"]
}
EOF

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "======================================================"
echo "  Demo resources created in ${REGION}"
echo "======================================================"
echo "  EC2 instances  : ${INSTANCE_IDS[*]}"
echo "  EBS volumes    : ${VOLUME_IDS[*]}"
echo "  EIP allocation : ${ALLOC_ID}  (${EIP})"
echo ""
echo "  State saved to: ${STATE_FILE}"
echo ""
echo "  Estimated monthly waste:"
echo "    EC2 × 3  : ~\$25.06  (~₹2,092)"
echo "    EBS × 2  : ~\$3.20   (~₹267)"
echo "    EIP      : ~\$3.60   (~₹300)"
echo "    Total    : ~\$31.86  (~₹2,659)"
echo ""
echo "  Run the scan:"
echo "    python -m scanner.main --regions ${REGION} --slack --output docs/demo-findings.json"
echo ""
echo "  Cleanup after demo:"
echo "    ./scripts/seed-demo-waste.sh --cleanup"
echo "======================================================"
