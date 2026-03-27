#!/usr/bin/env bash
# Dynamic Ansible inventory — reads Terraform outputs and emits JSON.
# Usage: ansible-playbook -i inventory.sh site.yml

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="${SCRIPT_DIR}/../terraform"

if ! terraform -chdir="${TF_DIR}" output -json ansible_inventory &>/dev/null; then
  echo '{"_meta":{"hostvars":{}},"all":{"hosts":[],"vars":{}}}'
  exit 0
fi

RAW=$(terraform -chdir="${TF_DIR}" output -raw ansible_inventory 2>/dev/null)

if [[ -z "${RAW}" ]]; then
  echo '{"_meta":{"hostvars":{}},"all":{"hosts":[],"vars":{}}}'
  exit 0
fi

echo "${RAW}" | jq .
