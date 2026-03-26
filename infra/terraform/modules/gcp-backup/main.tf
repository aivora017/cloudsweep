##############################################################################
# Module: gcp-backup
# Provisions a GCP Cloud Storage bucket for cross-cloud backup of CloudSweep
# scan reports (findings.json).
#
# Region: us-east1 / us-west1 / us-central1 — always-free tier eligible
#   (5 GB free per month at time of writing).
##############################################################################

resource "google_storage_bucket" "backup" {
  name          = "cloudsweep-backup-${var.env}-${var.gcp_project}"
  project       = var.gcp_project
  location      = upper(var.gcp_region)
  storage_class = "STANDARD"

  # Prevent accidental deletion of prod backups
  force_destroy = var.env != "prod"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 3
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    project     = "cloudsweep"
    environment = var.env
    managed-by  = "terraform"
  }
}

# Service account used by CloudSweep to write backups
resource "google_service_account" "backup_writer" {
  account_id   = "cloudsweep-backup-${var.env}"
  display_name = "CloudSweep Backup Writer (${var.env})"
  project      = var.gcp_project
}

# Grant only objectCreator + objectViewer – no bucket admin, no delete
resource "google_storage_bucket_iam_member" "writer" {
  bucket = google_storage_bucket.backup.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.backup_writer.email}"
}

resource "google_storage_bucket_iam_member" "viewer" {
  bucket = google_storage_bucket.backup.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.backup_writer.email}"
}

# HMAC key so the scanner can use S3-compatible GCS API
resource "google_storage_hmac_key" "backup_writer" {
  service_account_email = google_service_account.backup_writer.email
  project               = var.gcp_project
}
