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
  description = "Name of an existing EC2 key pair for SSH access to the server"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type for the CloudSweep server"
  type        = string
  default     = "t2.micro"
}

variable "allowed_ssh_cidr" {
  description = "CIDR allowed to SSH / reach admin ports. Restrict to your IP in prod."
  type        = string
  default     = "0.0.0.0/0"
}

variable "gcp_project" {
  description = "GCP project ID for cross-cloud backup bucket"
  type        = string
}

variable "gcp_region" {
  description = "GCP region for backup bucket (always-free eligible: us-east1, us-west1, us-central1)"
  type        = string
  default     = "us-east1"
}

# ---------------------------------------------------------------------------
# Remote-state backend (S3 + DynamoDB)
# Create these once manually, then reference them in the backend block below.
# Commands to bootstrap:
#   aws s3api create-bucket --bucket cloudsweep-tfstate-<account-id> \
#       --region ap-south-1 \
#       --create-bucket-configuration LocationConstraint=ap-south-1
#   aws s3api put-bucket-versioning --bucket cloudsweep-tfstate-<account-id> \
#       --versioning-configuration Status=Enabled
#   aws dynamodb create-table --table-name cloudsweep-tflock \
#       --attribute-definitions AttributeName=LockID,AttributeType=S \
#       --key-schema AttributeName=LockID,KeyType=HASH \
#       --billing-mode PAY_PER_REQUEST \
#       --region ap-south-1
# ---------------------------------------------------------------------------
variable "tf_state_bucket" {
  description = "S3 bucket name for Terraform remote state (bootstrapped manually)"
  type        = string
  default     = ""
}

variable "tf_lock_table" {
  description = "DynamoDB table name for Terraform state locking"
  type        = string
  default     = "cloudsweep-tflock"
}
