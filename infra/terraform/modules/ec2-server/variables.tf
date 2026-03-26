variable "env" {
  description = "Environment name (dev, prod)"
  type        = string
}

variable "region" {
  description = "AWS region to launch the instance in"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"
}

variable "key_name" {
  description = "Name of an existing EC2 key pair for SSH access"
  type        = string
}

variable "iam_instance_profile" {
  description = "IAM instance profile name to attach to the server"
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH into the server"
  type        = string
  default     = "0.0.0.0/0"
}
