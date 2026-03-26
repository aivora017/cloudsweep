output "bucket_name" {
  description = "Name of the CloudSweep reports S3 bucket"
  value       = aws_s3_bucket.reports.id
}

output "bucket_arn" {
  description = "ARN of the CloudSweep reports S3 bucket"
  value       = aws_s3_bucket.reports.arn
}

output "bucket_region" {
  description = "Region of the CloudSweep reports S3 bucket"
  value       = aws_s3_bucket.reports.region
}
