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

## CI/CD

GitHub Actions handles two things:

- `pr-checks.yml` runs on every pull request to main: flake8, bandit, pytest, and Dockerfile lint
- `scheduled-scan.yml` runs every Monday at 2AM UTC (7:30AM IST) via cron, plus a manual trigger button

AWS credentials in GitHub Actions use OIDC — no long-lived keys stored as secrets. Add these secrets to the repo:

- `AWS_ROLE_ARN` — IAM role ARN with read-only AWS access
- `DATABASE_URL` — PostgreSQL connection string
- `SLACK_WEBHOOK_URL` — Slack incoming webhook

Jenkins handles code changes through a four-stage pipeline: Lint → Test → Build and Push → Deploy. The `Jenkinsfile` is at the repo root. On feature branches only Lint and Test run. On main the full pipeline runs including Docker push to ghcr.io and Helm deploy.

Shared library functions are in `vars/` and get loaded when Jenkins is configured with this repo as a library named `cloudsweep`.

Jenkins setup:

```bash
docker run -d \
  --name jenkins \
  -p 8081:8080 \
  -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  jenkins/jenkins:lts
```

Then install Docker CLI inside the container so Jenkins can run Docker agents:

```bash
docker exec -u root jenkins apt-get update -qq && \
docker exec -u root jenkins apt-get install -y docker.io
```

Install plugins: Git, Docker Pipeline, Kubernetes CLI, Slack Notification.

Add credentials in Jenkins: `ghcr-token` (username/password), `kubeconfig` (secret file), `db-url` (secret text).

## Progress

This project is being built phase by phase:

- Phase 1: basic scanner and CLI
- Phase 2: Helm chart, k3s deployment, and PostgreSQL integration
- Phase 3: GitHub Actions scheduled scan and Jenkins CI/CD pipeline

## Layout

```text
scanner/      scanner code
notifier/     Slack notifier
db/           SQL migration
helm/         Helm chart
scripts/      helper scripts
vars/         Jenkins shared library functions
```
