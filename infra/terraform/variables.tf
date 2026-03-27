variable "env" {
  description = "Environment name: dev or prod"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "prod"], var.env)
    error_message = "env must be 'dev' or 'prod'."
  }
}

variable "aws_region" {
  description = "Primary AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "key_name" {
  description = "Name of an existing EC2 key pair for SSH access"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"
}

variable "allowed_ssh_cidr" {
  description = "CIDR allowed to reach SSH and admin ports. Restrict to your IP in prod."
  type        = string
  default     = "0.0.0.0/0"
}

variable "gcp_project" {
  description = "GCP project ID for the backup bucket"
  type        = string
}

variable "gcp_region" {
  description = "GCP region for the backup bucket (us-east1/us-west1/us-central1 are always-free)"
  type        = string
  default     = "us-east1"
}
