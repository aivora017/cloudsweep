data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }

  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
  }
}

data "aws_iam_policy_document" "scanner_permissions" {
  statement {
    sid       = "EC2ReadOnly"
    actions   = ["ec2:Describe*"]
    resources = ["*"]
  }

  statement {
    sid       = "CloudWatchReadOnly"
    actions   = ["cloudwatch:GetMetricStatistics", "cloudwatch:ListMetrics"]
    resources = ["*"]
  }

  statement {
    sid       = "CostExplorerReadOnly"
    actions   = ["ce:GetCostAndUsage", "ce:GetRightsizingRecommendation"]
    resources = ["*"]
  }

  statement {
    sid       = "RDSReadOnly"
    actions   = ["rds:Describe*"]
    resources = ["*"]
  }

  statement {
    sid       = "ELBReadOnly"
    actions   = ["elasticloadbalancing:Describe*"]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "scanner" {
  name   = "cloudsweep-scanner-${var.env}"
  policy = data.aws_iam_policy_document.scanner_permissions.json
}

resource "aws_iam_role" "scanner" {
  name               = "cloudsweep-scanner-${var.env}"
  assume_role_policy = data.aws_iam_policy_document.trust.json
}

resource "aws_iam_role_policy_attachment" "scanner" {
  role       = aws_iam_role.scanner.name
  policy_arn = aws_iam_policy.scanner.arn
}

resource "aws_iam_instance_profile" "scanner" {
  name = "cloudsweep-scanner-${var.env}"
  role = aws_iam_role.scanner.name
}
