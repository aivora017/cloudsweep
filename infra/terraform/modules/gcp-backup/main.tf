resource "google_storage_bucket" "backup" {
  name          = "cloudsweep-backup-${var.env}-${var.gcp_project}"
  project       = var.gcp_project
  location      = upper(var.gcp_region)
  storage_class = "STANDARD"

  # don't protect dev buckets from terraform destroy
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
    project    = "cloudsweep"
    env        = var.env
    managed-by = "terraform"
  }
}

resource "google_service_account" "backup_writer" {
  account_id   = "cloudsweep-backup-${var.env}"
  display_name = "CloudSweep backup writer (${var.env})"
  project      = var.gcp_project
}

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

resource "google_storage_hmac_key" "backup_writer" {
  service_account_email = google_service_account.backup_writer.email
  project               = var.gcp_project
}
