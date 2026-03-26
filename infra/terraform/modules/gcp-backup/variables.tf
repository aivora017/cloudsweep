variable "env" {
  description = "Environment name (dev, prod)"
  type        = string
}

variable "gcp_project" {
  description = "GCP project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP region — use always-free eligible regions: us-east1, us-west1, us-central1"
  type        = string
  default     = "us-east1"
}
