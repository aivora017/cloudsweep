terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # S3 bucket must exist before terraform init.
  # Run infra-up.sh which handles the bootstrap, or see README.
  backend "s3" {
    key            = "cloudsweep/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "cloudsweep-tflock"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "cloudsweep"
      Environment = var.env
      ManagedBy   = "terraform"
    }
  }
}

provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}

module "iam_scanner_role" {
  source = "./modules/iam-scanner-role"
  env    = var.env
}

module "s3_reports" {
  source = "./modules/s3-reports"
  env    = var.env
  region = var.aws_region
}

module "ec2_server" {
  source = "./modules/ec2-server"

  env                  = var.env
  region               = var.aws_region
  instance_type        = var.instance_type
  key_name             = var.key_name
  iam_instance_profile = module.iam_scanner_role.instance_profile_name
  allowed_ssh_cidr     = var.allowed_ssh_cidr

  depends_on = [module.iam_scanner_role]
}

module "gcp_backup" {
  source      = "./modules/gcp-backup"
  env         = var.env
  gcp_project = var.gcp_project
  gcp_region  = var.gcp_region
}
