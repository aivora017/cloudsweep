output "role_arn" {
  description = "ARN of the CloudSweep scanner IAM role"
  value       = aws_iam_role.scanner.arn
}

output "role_name" {
  description = "Name of the CloudSweep scanner IAM role"
  value       = aws_iam_role.scanner.name
}

output "instance_profile_name" {
  description = "Name of the IAM instance profile attached to the scanner role"
  value       = aws_iam_instance_profile.scanner.name
}

output "policy_arn" {
  description = "ARN of the least-privilege scanner policy"
  value       = aws_iam_policy.scanner.arn
}
