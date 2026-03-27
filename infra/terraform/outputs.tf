output "server_ip" {
  value = module.ec2_server.public_ip
}

output "instance_id" {
  value = module.ec2_server.instance_id
}

output "iam_role_arn" {
  value = module.iam_scanner_role.role_arn
}

output "iam_instance_profile" {
  value = module.iam_scanner_role.instance_profile_name
}

output "reports_bucket" {
  value = module.s3_reports.bucket_name
}

output "gcp_backup_bucket" {
  value = module.gcp_backup.bucket_name
}

# consumed by infra/ansible/inventory.sh
output "ansible_inventory" {
  value = jsonencode({
    all = {
      hosts = {
        cloudsweep_server = {
          ansible_host   = module.ec2_server.public_ip
          ansible_user   = "ec2-user"
          iam_role_arn   = module.iam_scanner_role.role_arn
          reports_bucket = module.s3_reports.bucket_name
          aws_region     = var.aws_region
        }
      }
    }
  })
}
