#!/usr/bin/env bash
# seed-demo-waste.sh
# Creates demo AWS resources to show CloudSweep finding real waste:
#   3 idle t2.micro EC2 instances, 2 unattached 20GB EBS volumes, 1 unused EIP
# Usage: ./scripts/seed-demo-waste.sh [--region ap-south-1] [--key-name <keypair>]
# Cleanup: ./scripts/seed-demo-waste.sh --cleanup

set -euo pipefail

REGION="ap-south-1"
KEY_NAME=""
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

if [[ "${CLEANUP}" == "true" ]]; then
  if [[ ! -f "${STATE_FILE}" ]]; then
    echo "ERROR: state file not found at ${STATE_FILE}"
    exit 1
  fi

  INSTANCE_IDS=$(jq -r '.instances[]' "${STATE_FILE}" | tr '\n' ' ')
  VOLUME_IDS=$(jq -r '.volumes[]' "${STATE_FILE}" | tr '\n' ' ')
  ALLOC_IDS=$(jq -r '.eip_allocations[]' "${STATE_FILE}" | tr '\n' ' ')

  echo "Terminating EC2 instances..."
  aws ec2 terminate-instances --instance-ids ${INSTANCE_IDS} --region "${REGION}" > /dev/null
  aws ec2 wait instance-terminated --instance-ids ${INSTANCE_IDS} --region "${REGION}"

  echo "Deleting EBS volumes..."
  for vol in ${VOLUME_IDS}; do
    aws ec2 delete-volume --volume-id "${vol}" --region "${REGION}"
  done

  echo "Releasing EIPs..."
  for alloc in ${ALLOC_IDS}; do
    aws ec2 release-address --allocation-id "${alloc}" --region "${REGION}"
  done

  rm -f "${STATE_FILE}"
  echo "Done. All demo resources deleted."
  exit 0
fi

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

echo "Launching 3 x t2.micro instances..."
LAUNCH_ARGS=(
  --image-id "${AMI_ID}"
  --instance-type t2.micro
  --count 3
  --no-associate-public-ip-address
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=cloudsweep-demo-idle},{Key=Project,Value=cloudsweep},{Key=Demo,Value=true}]"
  --region "${REGION}"
  --query 'Instances[*].InstanceId'
  --output text
)
if [[ -n "${KEY_NAME}" ]]; then
  LAUNCH_ARGS+=(--key-name "${KEY_NAME}")
fi

INSTANCE_IDS_RAW=$(aws ec2 run-instances "${LAUNCH_ARGS[@]}")
INSTANCE_IDS=($INSTANCE_IDS_RAW)
aws ec2 wait instance-running --instance-ids "${INSTANCE_IDS[@]}" --region "${REGION}"
echo "  Running: ${INSTANCE_IDS[*]}"

echo "Creating 2 x 20GB unattached EBS volumes..."
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
    --tag-specifications "ResourceType=volume,Tags=[{Key=Name,Value=cloudsweep-demo-orphan-${i}},{Key=Project,Value=cloudsweep},{Key=Demo,Value=true}]" \
    --query 'VolumeId' \
    --output text \
    --region "${REGION}")
  VOLUME_IDS+=("${VOL_ID}")
  echo "  Created: ${VOL_ID}"
done

echo "Allocating unused EIP..."
ALLOC_ID=$(aws ec2 allocate-address \
  --domain vpc \
  --tag-specifications "ResourceType=elastic-ip,Tags=[{Key=Name,Value=cloudsweep-demo-unused-eip},{Key=Project,Value=cloudsweep},{Key=Demo,Value=true}]" \
  --query 'AllocationId' \
  --output text \
  --region "${REGION}")
EIP=$(aws ec2 describe-addresses --allocation-ids "${ALLOC_ID}" --query 'Addresses[0].PublicIp' --output text --region "${REGION}")
echo "  ${ALLOC_ID} (${EIP})"

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

echo ""
echo "Done. Resources saved to ${STATE_FILE}"
echo ""
echo "Estimated monthly waste: ~\$31.86 (~₹2,659)"
echo "  EC2 x3: ~\$25.06  |  EBS x2: ~\$3.20  |  EIP: ~\$3.60"
echo ""
echo "Run the scan:"
echo "  python -m scanner.main --regions ${REGION} --slack --output docs/demo-findings.json"
echo ""
echo "Cleanup after demo:"
echo "  ./scripts/seed-demo-waste.sh --cleanup"
