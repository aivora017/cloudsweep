variable "env" {
  description = "Environment name (dev, prod)"
  type        = string
}

variable "ec2_instance_role_name" {
  description = "Name of the EC2 instance role that may assume the scanner role"
  type        = string
  default     = ""
}
