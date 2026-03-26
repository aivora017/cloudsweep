variable "env" {
  description = "Environment name (dev, prod)"
  type        = string
}

variable "region" {
  description = "AWS region for the bucket"
  type        = string
}

variable "lifecycle_days" {
  description = "Days after which report objects expire"
  type        = number
  default     = 90
}
