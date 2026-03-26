output "bucket_name" {
  description = "Name of the GCP backup bucket"
  value       = google_storage_bucket.backup.name
}

output "bucket_url" {
  description = "gs:// URL of the backup bucket"
  value       = "gs://${google_storage_bucket.backup.name}"
}

output "service_account_email" {
  description = "Email of the GCP service account for backup writes"
  value       = google_service_account.backup_writer.email
}

output "hmac_access_id" {
  description = "HMAC access ID (S3-compatible key) for the backup writer"
  value       = google_storage_hmac_key.backup_writer.access_id
  sensitive   = true
}

output "hmac_secret" {
  description = "HMAC secret (S3-compatible key) for the backup writer"
  value       = google_storage_hmac_key.backup_writer.secret
  sensitive   = true
}
