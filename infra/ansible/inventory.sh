#!/usr/bin/env bash
##############################################################################
# Dynamic Ansible inventory — reads Terraform outputs and emits JSON.
#
# Usage (Ansible picks it up automatically because the file is executable):
#   ansible-playbook -i inventory.sh site.yml
#
# Requirements:
#   - terraform must be installed and `infra/terraform/` must be initialised
#   - jq must be installed
##############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="${SCRIPT_DIR}/../terraform"

# Emit empty inventory if Terraform hasn't been applied yet
if ! terraform -chdir="${TF_DIR}" output -json ansible_inventory &>/dev/null; then
  echo '{"_meta":{"hostvars":{}},"all":{"hosts":[],"vars":{}}}'
  exit 0
fi

# Read the ansible_inventory output (a JSON string inside a JSON string)
RAW=$(terraform -chdir="${TF_DIR}" output -raw ansible_inventory 2>/dev/null)

if [[ -z "${RAW}" ]]; then
  echo '{"_meta":{"hostvars":{}},"all":{"hosts":[],"vars":{}}}'
  exit 0
fi

# ansible_inventory is already a valid Ansible dynamic inventory JSON blob
echo "${RAW}" | jq .
