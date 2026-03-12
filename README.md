# CloudSweep

CloudSweep scans AWS for idle resources and estimates monthly waste in USD and INR.

## Scope

- EC2 instances with low CPU usage
- Unattached EBS volumes
- Unused Elastic IPs
- Underused RDS instances
- Old EBS snapshots

Results are written as JSON and can also be stored in PostgreSQL.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set AWS credentials before running a real scan:

```bash
export AWS_ACCESS_KEY_ID=xxx
export AWS_SECRET_ACCESS_KEY=xxx
export AWS_DEFAULT_REGION=ap-south-1
```

## Run

Directly:

```bash
python -m scanner.main --regions ap-south-1,us-east-1 --output findings.json
```

With helper script:

```bash
./scripts/run-scan.sh
```

With Docker Compose:

```bash
docker-compose up postgres
docker-compose --profile scanner up
```

## Helm

The Helm chart is in `helm/cloudsweep`.

Useful files:

- `helm/cloudsweep/values.yaml`
- `helm/cloudsweep/values-dev.yaml`
- `helm/cloudsweep/values-prod.yaml`
- `helm/cloudsweep/templates/cronjob.yaml`
- `helm/cloudsweep/templates/postgresql-statefulset.yaml`
- `helm/cloudsweep/templates/postgresql-service.yaml`
- `helm/cloudsweep/templates/pre-install-job.yaml`

Install on k3s:

```bash
helm install cloudsweep ./helm/cloudsweep --namespace cloudsweep --create-namespace
```

## Phase 2 result

Verified on local k3s:

- k3s node Ready
- Helm release deployed
- CronJob schedule active: `0 2 * * 1`
- PostgreSQL StatefulSet running
- PostgreSQL PVC bound
- Manual trigger completed successfully
- Findings stored in PostgreSQL with INR values

Latest proof run:

- 6 findings
- total waste: `₹6433.41`
- latest stored scan: `scan_run_id: 17`

## Tests

```bash
pytest -q
```

Current result: `22 passed`

## Layout

```text
scanner/      scanner code
notifier/     Slack notifier
db/           SQL migration
helm/         Helm chart
scripts/      helper scripts
tests/        unit tests
```
