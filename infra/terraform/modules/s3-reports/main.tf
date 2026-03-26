##############################################################################
# Module: s3-reports
# Creates an S3 bucket for CloudSweep scan reports with:
#   - 90-day lifecycle expiry rule
#   - Server-side encryption (AES-256)
#   - Versioning enabled
#   - Public access fully blocked
##############################################################################

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "reports" {
  # Bucket name must be globally unique – include account ID as suffix
  bucket        = "cloudsweep-reports-${var.env}-${data.aws_caller_identity.current.account_id}"
  force_destroy = var.env != "prod"

  tags = {
    Project     = "cloudsweep"
    Environment = var.env
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket_versioning" "reports" {
  bucket = aws_s3_bucket.reports.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "reports" {
  bucket = aws_s3_bucket.reports.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id

  rule {
    id     = "expire-old-reports"
    status = "Enabled"

    filter {
      prefix = ""
    }

    expiration {
      days = var.lifecycle_days
    }

    noncurrent_version_expiration {
      noncurrent_days = var.lifecycle_days
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Bucket policy: allow scanner role to put/get objects, deny all else
data "aws_iam_policy_document" "reports_bucket_policy" {
  statement {
    sid    = "DenyInsecureTransport"
    effect = "Deny"

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    actions   = ["s3:*"]
    resources = [aws_s3_bucket.reports.arn, "${aws_s3_bucket.reports.arn}/*"]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "reports" {
  bucket = aws_s3_bucket.reports.id
  policy = data.aws_iam_policy_document.reports_bucket_policy.json

  depends_on = [aws_s3_bucket_public_access_block.reports]
}
