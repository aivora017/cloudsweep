##############################################################################
# Module: iam-scanner-role
# Creates a least-privilege read-only IAM role for the CloudSweep scanner.
#
# Allowed actions (read-only, no create/modify/delete):
#   ec2:Describe*                            – EC2 + EBS scanning
#   cloudwatch:GetMetricStatistics           – CPU utilisation data
#   cloudwatch:ListMetrics                   – discover available metrics
#   ce:GetCostAndUsage                       – Cost Explorer waste data
#   ce:GetRightsizingRecommendation          – right-sizing hints
#   rds:Describe*                            – RDS scanning
#   elasticloadbalancing:Describe*           – unused LB detection
##############################################################################

data "aws_caller_identity" "current" {}

# ---------------------------------------------------------------------------
# Trust policy – EC2 instances in the same account may assume this role.
# The root account is also listed so humans can assume it for manual audits.
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "trust" {
  statement {
    sid     = "AllowEC2Assume"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }

  statement {
    sid     = "AllowRootAudit"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
  }
}

# ---------------------------------------------------------------------------
# Least-privilege permission policy
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "scanner_permissions" {
  # EC2 + EBS scanning
  statement {
    sid    = "EC2ReadOnly"
    effect = "Allow"
    actions = [
      "ec2:Describe*",
    ]
    resources = ["*"]
  }

  # CloudWatch CPU metrics
  statement {
    sid    = "CloudWatchReadOnly"
    effect = "Allow"
    actions = [
      "cloudwatch:GetMetricStatistics",
      "cloudwatch:ListMetrics",
    ]
    resources = ["*"]
  }

  # Cost Explorer
  statement {
    sid    = "CostExplorerReadOnly"
    effect = "Allow"
    actions = [
      "ce:GetCostAndUsage",
      "ce:GetRightsizingRecommendation",
    ]
    resources = ["*"]
  }

  # RDS scanning
  statement {
    sid    = "RDSReadOnly"
    effect = "Allow"
    actions = [
      "rds:Describe*",
    ]
    resources = ["*"]
  }

  # Elastic Load Balancing – unused LB detection
  statement {
    sid    = "ELBReadOnly"
    effect = "Allow"
    actions = [
      "elasticloadbalancing:Describe*",
    ]
    resources = ["*"]
  }

  # Explicit deny – belt-and-suspenders: block anything mutating
  statement {
    sid    = "DenyAllWrites"
    effect = "Deny"
    not_actions = [
      "ec2:Describe*",
      "cloudwatch:GetMetricStatistics",
      "cloudwatch:ListMetrics",
      "ce:GetCostAndUsage",
      "ce:GetRightsizingRecommendation",
      "rds:Describe*",
      "elasticloadbalancing:Describe*",
      "sts:AssumeRole",
      "sts:GetCallerIdentity",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "scanner" {
  name        = "cloudsweep-scanner-${var.env}"
  description = "Least-privilege read-only policy for CloudSweep scanner (${var.env})"
  policy      = data.aws_iam_policy_document.scanner_permissions.json

  tags = {
    Project     = "cloudsweep"
    Environment = var.env
    ManagedBy   = "terraform"
  }
}

resource "aws_iam_role" "scanner" {
  name               = "cloudsweep-scanner-${var.env}"
  assume_role_policy = data.aws_iam_policy_document.trust.json
  description        = "CloudSweep scanner role – read-only AWS access (${var.env})"

  tags = {
    Project     = "cloudsweep"
    Environment = var.env
    ManagedBy   = "terraform"
  }
}

resource "aws_iam_role_policy_attachment" "scanner" {
  role       = aws_iam_role.scanner.name
  policy_arn = aws_iam_policy.scanner.arn
}

# Instance profile so EC2 can carry the role
resource "aws_iam_instance_profile" "scanner" {
  name = "cloudsweep-scanner-${var.env}"
  role = aws_iam_role.scanner.name

  tags = {
    Project     = "cloudsweep"
    Environment = var.env
    ManagedBy   = "terraform"
  }
}
