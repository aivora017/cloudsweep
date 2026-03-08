# CloudSweep

AWS cost optimization scanner. Identifies waste in your AWS account.

## What it does

Scans your AWS account for idle resources:
- EC2 instances with low CPU (< 5% over 7 days)
- Orphaned EBS volumes (unattached)
- Unused Elastic IPs
- Idle RDS instances (low connections)
- Old snapshots (> 30 days)

Returns findings as JSON with monthly cost in USD and INR.

## Setup

```bash
git clone https://github.com/aivora017/cloudsweep.git
cd cloudsweep

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Configure AWS credentials:
```bash
export AWS_ACCESS_KEY_ID=xxx
export AWS_SECRET_ACCESS_KEY=xxx
export AWS_DEFAULT_REGION=ap-south-1
```

## Run the scanner

```bash
python -m scanner.main --regions ap-south-1,us-east-1 --output findings.json
```

Or with Docker:
```bash
docker-compose up postgres
docker-compose --profile scanner up
```

## Output

```json
{
  "findings": [
    {
      "resource_id": "i-123456",
      "resource_type": "EC2",
      "region": "ap-south-1",
      "reason": "CPU avg 2.3% over 7 days",
      "monthly_cost_usd": 30.50,
      "monthly_cost_inr": 2547.75,
      "tags": {"Name": "test-server"},
      "detected_at": "2026-03-06T10:30:45Z"
    }
  ],
  "summary": {
    "total_findings": 1,
    "total_waste_usd": 30.50,
    "total_waste_inr": 2547.75,
    "regions_scanned": ["ap-south-1"],
    "scanned_at": "2026-03-06T10:30:45Z"
  }
}
```

## Project structure

```
scanner/          - Scanning functions
notifier/         - Slack integration
db/               - PostgreSQL schema and manager
tests/            - Unit tests
scripts/          - Utilities
ec2_pricing/      - Instance pricing data (CSV)
```

## Tests

```bash
pytest tests/ -v
```

All 5 scan functions tested with moto (AWS mocks).

## Requirements

- Python 3.11+
- boto3
- PostgreSQL
- Docker (optional)
