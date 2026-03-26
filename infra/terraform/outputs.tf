output "server_ip" {
  description = "Public Elastic IP of the CloudSweep EC2 server"
  value       = module.ec2_server.public_ip
}

output "instance_id" {
  description = "EC2 instance ID"
  value       = module.ec2_server.instance_id
}

output "iam_role_arn" {
  description = "ARN of the CloudSweep scanner IAM role"
  value       = module.iam_scanner_role.role_arn
}

output "iam_instance_profile" {
  description = "Name of the IAM instance profile attached to the server"
  value       = module.iam_scanner_role.instance_profile_name
}

output "reports_bucket" {
  description = "Name of the S3 reports bucket"
  value       = module.s3_reports.bucket_name
}

output "reports_bucket_arn" {
  description = "ARN of the S3 reports bucket"
  value       = module.s3_reports.bucket_arn
}

output "gcp_backup_bucket" {
  description = "GCP backup bucket name"
  value       = module.gcp_backup.bucket_name
}

output "gcp_backup_bucket_url" {
  description = "gs:// URL of the GCP backup bucket"
  value       = module.gcp_backup.bucket_url
}

output "gcp_service_account" {
  description = "GCP service account email for backup writes"
  value       = module.gcp_backup.service_account_email
}

# Used by Ansible inventory.sh
output "ansible_inventory" {
  description = "JSON snippet consumed by infra/ansible/inventory.sh"
  value = jsonencode({
    all = {
      hosts = {
        cloudsweep_server = {
          ansible_host         = module.ec2_server.public_ip
          ansible_user         = "ec2-user"
          iam_role_arn         = module.iam_scanner_role.role_arn
          reports_bucket       = module.s3_reports.bucket_name
          aws_region           = var.aws_region
        }
      }
    }
  })
}
