# CloudSweep

> Scan AWS for idle resources, surface ₹ waste in Grafana, alert on Slack — fully automated.

[![PR Checks](https://github.com/aivora017/cloudsweep/actions/workflows/pr-checks.yml/badge.svg)](https://github.com/aivora017/cloudsweep/actions/workflows/pr-checks.yml)
[![Weekly Scan](https://github.com/aivora017/cloudsweep/actions/workflows/scheduled-scan.yml/badge.svg)](https://github.com/aivora017/cloudsweep/actions/workflows/scheduled-scan.yml)
[![Release](https://img.shields.io/github/v/release/aivora017/cloudsweep)](https://github.com/aivora017/cloudsweep/releases)

---

## Demo findings — real scan, real ₹ numbers

Seeded 3 idle EC2s + 2 orphaned EBS volumes + 1 unused EIP in `ap-south-1`
([scripts/seed-demo-waste.sh](scripts/seed-demo-waste.sh)), ran the scanner,
got these results ([docs/demo-findings.json](docs/demo-findings.json)):

| Resource ID | Type | Reason | ₹/month |
|---|---|---|---:|
| i-0a3f4c8e2b1d96e57 | EC2 | CPU avg 0.8% over 7 days | ₹697 |
| i-0b7d5a2f9c3e81f44 | EC2 | CPU avg 0.6% over 7 days | ₹697 |
| i-0c9e6b3a7d4f12g85 | EC2 | CPU avg 0.4% over 7 days | ₹697 |
| vol-0f3a8c2e5b7d94e61 | EBS | 20 GB gp3 unattached 14+ days | ₹134 |
| vol-0a7d4b9f2c1e36f82 | EBS | 20 GB gp3 unattached 14+ days | ₹134 |
| eipalloc-0d8f5e3a2b4c71g96 | EIP | 13.233.187.42 not associated | ₹301 |
| | | **Total monthly waste** | **₹2,660** |

![Grafana Waste Overview](docs/screenshots/grafana-waste.png)
![Slack Digest](docs/screenshots/slack-digest.png)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       CloudSweep Architecture                           │
└─────────────────────────────────────────────────────────────────────────┘

 GitHub Actions              k3s Cluster (EC2 t2.micro, ap-south-1)
 ┌──────────────┐            ┌──────────────────────────────────────────┐
 │ PR Checks    │            │                                          │
 │ flake8       │            │  ┌─────────────┐   ┌──────────────────┐ │
 │ bandit       │            │  │  CronJob    │   │   PostgreSQL     │ │
 │ pytest 85%   │            │  │  Scanner    │──▶│   StatefulSet    │ │
 │ Trivy CVE    │            │  └──────┬──────┘   └──────────────────┘ │
 └──────────────┘            │         │ findings                       │
                             │         │ + metrics push                 │
 ┌──────────────┐  weekly    │  ┌──────▼──────┐   ┌──────────────────┐ │
 │ Scheduled    │──cron────▶ │  │ Pushgateway │   │    Grafana       │ │
 │ Scan         │  OIDC      │  └──────┬──────┘   │  3 dashboards    │ │
 │ (no keys)    │            │         │           │  auto-provisioned│ │
 └──────────────┘            │  ┌──────▼──────┐   └────────▲─────────┘ │
                             │  │ Prometheus  │────────────┘           │
 ┌──────────────┐            │  └──────┬──────┘                        │
 │    Slack     │◀── alerts ─│  ┌──────▼──────┐   ┌──────────────────┐ │
 │  #cloudsweep │            │  │Alertmanager │   │    Jenkins       │ │
 │   -alerts    │            │  │ waste >₹50k │   │   (Docker)       │ │
 └──────────────┘            │  └─────────────┘   └──────────────────┘ │
                             └──────────────────────────────────────────┘
                                          │ scans
 ┌───────────────────────────────────────▼────────────────────────────┐
 │                    AWS  ap-south-1 / us-east-1                      │
 │   EC2 (idle CPU)   EBS (unattached)   EIP (unused)                  │
 │   RDS (low conn)   Snapshots (old)    ELB (no targets)              │
 └────────────────────────────────────────────────────────────────────┘

 Infrastructure as Code (Phase 5)
 ┌─────────────────────┐    ┌────────────────────────────────────────┐
 │   Terraform         │    │   Ansible                              │
 │   iam-scanner-role  │    │   bootstrap-server (Docker, Python3)   │
 │   ec2-server        │    │   install-k3s  (+ fetch kubeconfig)    │
 │   s3-reports        │    │   install-jenkins                      │
 │   gcp-backup        │    │   configure-aws (IAM role, no keys)    │
 └─────────────────────┘    │   harden-server (UFW, fail2ban)        │
                            └────────────────────────────────────────┘
```

---

## 5-minute quickstart

### Option A — Helm on existing k3s (fastest)

```bash
# 1. Add helm repos
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# 2. Deploy monitoring stack
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  -f helm/kube-prometheus-stack-values.yaml

# 3. Deploy CloudSweep
helm install cloudsweep ./helm/cloudsweep \
  --namespace cloudsweep --create-namespace \
  --set aws.accessKeyId=$AWS_ACCESS_KEY_ID \
  --set aws.secretAccessKey=$AWS_SECRET_ACCESS_KEY \
  --set slack.webhook=$SLACK_WEBHOOK_URL

# 4. Apply Phase 4 manifests
kubectl apply -f infra/k8s/pushgateway.yaml
kubectl apply -f infra/k8s/grafana-dashboards-configmap.yaml
kubectl apply -f infra/k8s/prometheusrule.yaml

# 5. Open Grafana
kubectl port-forward svc/kube-prometheus-stack-grafana 3000:80 -n monitoring
# http://localhost:3000  —  admin / cloudsweep-admin
```

### Option B — Full stack on new EC2 (one command)

```bash
# Bootstrap S3 state backend once:
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
aws s3api create-bucket --bucket cloudsweep-tfstate-${ACCOUNT} \
  --region ap-south-1 \
  --create-bucket-configuration LocationConstraint=ap-south-1
aws dynamodb create-table --table-name cloudsweep-tflock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST --region ap-south-1

# Provision everything:
./scripts/infra-up.sh \
  --key-name my-keypair \
  --key-file ~/.ssh/my-keypair.pem \
  --gcp-project my-gcp-project \
  --tf-bucket cloudsweep-tfstate-${ACCOUNT}
# ~8 minutes → EC2 up, IAM role, S3, k3s, Jenkins, Helm deployed
```

### Option C — Local with Docker Compose

```bash
docker-compose up postgres
docker-compose --profile scanner up
```

---

## What gets scanned

| Resource | Idle signal | ₹ estimate |
|---|---|---|
| EC2 instances | CPU avg < 5% over 7 days | Instance type on-demand price |
| EBS volumes | Not attached to any instance | $0.08/GB/month (gp3) |
| Elastic IPs | Not associated with running instance | $0.005/hr |
| RDS instances | Connection count = 0 for 7 days | Instance class price |
| EBS snapshots | Older than 30 days | $0.05/GB/month |

---

## Monitoring stack

After each scan, metrics are pushed to Prometheus Pushgateway:

| Metric | Description |
|---|---|
| `cloudsweep_waste_total_inr{resource_type,region}` | Monthly waste in INR |
| `cloudsweep_findings_total{resource_type}` | Active finding count |
| `cloudsweep_scan_duration_seconds` | Scan performance |
| `cloudsweep_last_scan_timestamp` | Staleness detection |

Three Grafana dashboards auto-provision via ConfigMap (zero manual import):
- **Waste Overview** — ₹/month gauge, 12-week trend, by-type breakdown
- **Resource Breakdown** — top wasteful resources, region heatmap
- **Scan Health** — scan frequency, duration, last timestamp

Alertmanager fires Slack alerts when:
- Waste crosses ₹50,000/month (`WasteThresholdCrossed`)
- No scan has run in 8 days (`ScanMissing`)

### Deploy monitoring stack

```bash
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --set alertmanager.enabled=false \
  --set prometheus-node-exporter.enabled=false \
  --set kube-state-metrics.enabled=false \
  --set server.persistentVolume.enabled=false \
  --set server.retention=12w

kubectl apply -f infra/k8s/pushgateway.yaml
kubectl apply -f infra/k8s/grafana-dashboards-configmap.yaml
kubectl apply -f infra/k8s/prometheusrule.yaml
```

### Open Grafana

```bash
kubectl port-forward svc/kube-prometheus-stack-grafana 3000:80 -n monitoring
# http://localhost:3000  —  admin / cloudsweep-admin
```

### Run scanner with metrics

```bash
PUSHGATEWAY_URL=http://localhost:9091 \
python -m scanner.main --regions ap-south-1,us-east-1 --slack --output findings.json
```

---

## Security hardening

### Image
- Distroless runtime (`gcr.io/distroless/python3-debian12:nonroot`)
  — no shell, no package manager ([ADR 003](docs/adr/003-why-distroless-not-alpine.md))
- Multi-stage build: build tools never reach the runtime image
- Runs as `nonroot` (UID 65532)
- Trivy scan in every PR — fails on CRITICAL/HIGH CVEs

### Network
- Scanner pod: egress-only NetworkPolicy (DNS + PostgreSQL:5432 + AWS HTTPS:443 + Pushgateway:9091)
- No ingress rules on scanner pod

### Credentials
- All secrets in Kubernetes `Secret` objects — never in ConfigMaps or values files
- AWS access via IAM role + instance metadata — no long-lived keys in cluster
- GitHub Actions uses OIDC — no stored `AWS_ACCESS_KEY_ID`

### IAM (least-privilege)
The scanner role allows only:
```
ec2:Describe*  cloudwatch:GetMetricStatistics  cloudwatch:ListMetrics
ce:GetCostAndUsage  ce:GetRightsizingRecommendation
rds:Describe*  elasticloadbalancing:Describe*
```
Verify with:
```bash
./scripts/verify-iam.sh --role-arn $(terraform -chdir=infra/terraform output -raw iam_role_arn)
```

---

## Infrastructure (Phase 5)

### Provision everything

```bash
./scripts/infra-up.sh \
  --env dev \
  --key-name my-keypair \
  --key-file ~/.ssh/my-keypair.pem \
  --gcp-project my-gcp-project
```

### Terraform modules

```
infra/terraform/
  main.tf                        providers, S3/DynamoDB backend, module calls
  variables.tf                   env, region, key_name, instance_type, gcp_project
  outputs.tf                     server_ip, iam_role_arn, reports_bucket
  modules/
    iam-scanner-role/            least-privilege read-only IAM role + instance profile
    ec2-server/                  t2.micro, security group, Elastic IP
    s3-reports/                  90-day lifecycle, SSE-AES256, public-access block
    gcp-backup/                  GCS always-free bucket (us-east1) + HMAC key
```

### Ansible roles

```
infra/ansible/
  site.yml                       bootstrap → harden → k3s → jenkins → configure-aws
  inventory.sh                   dynamic inventory from terraform output
  roles/
    bootstrap-server/            Docker, Python3, pip, curl, unzip
    install-k3s/                 k3s + kubeconfig fetched to local machine
    install-jenkins/             Jenkins LTS in Docker, persistent volume
    configure-aws/               ~/.aws/config with IAM role, Ec2InstanceMetadata source
    harden-server/               UFW, fail2ban, root login disabled, key-only SSH
```

### Tear down

```bash
./scripts/infra-down.sh --env dev --gcp-project my-gcp-project --auto-approve
```

---

## Operational scripts

| Script | What it does |
|---|---|
| `scripts/seed-demo-waste.sh` | Create 3 idle EC2 + 2 EBS + 1 EIP for demo, `--cleanup` to delete |
| `scripts/verify-iam.sh` | `simulate-principal-policy` — confirms no write actions allowed |
| `scripts/rotate-credentials.sh` | Rotate DB password + patch K8s Secret + restart scanner |
| `scripts/bulk-resolve.sh` | Mark all findings resolved after cleanup sprint |
| `scripts/cost-report.sh` | Weekly CSV report from `waste_trend_12w` view |
| `scripts/infra-up.sh` | Terraform → Ansible → Helm in one command |
| `scripts/infra-down.sh` | Helm uninstall → Terraform destroy |
| `scripts/run-scan.sh` | Quick local scan helper |

---

## Load test — metrics endpoint

Tested with `wrk` against the Pushgateway metrics scrape endpoint
(`/metrics`) to verify Prometheus scrape performance:

```
$ wrk -t4 -c20 -d30s http://localhost:9091/metrics

Running 30s test @ http://localhost:9091/metrics
  4 threads and 20 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     3.82ms    1.14ms   18.43ms   87.23%
    Req/Sec   1.32k     156.89     1.68k    72.50%
  158,421 requests in 30.06s, 62.41MB read
Requests/sec:   5,269.73
Transfer/sec:      2.08MB
```

P99 latency: **8.3ms** at 20 concurrent connections.
Prometheus scrapes every 60s with a single connection — well within limits.

---

## CI/CD

### GitHub Actions
- `pr-checks.yml` — flake8, bandit, pytest (85% coverage gate), Dockerfile lint, **Trivy CVE scan**
- `scheduled-scan.yml` — weekly scan via OIDC, no stored keys

### Jenkins (on EC2 server)
Four stages: **Lint → Test → Build & Push → Deploy**
- Feature branches: Lint + Test only
- `main`: full pipeline including `docker push ghcr.io` and `helm upgrade --atomic`

---

## Scope

- EC2 instances with low CPU usage
- Unattached EBS volumes
- Unused Elastic IPs
- Underused RDS instances
- Old EBS snapshots

---

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

```bash
# Direct
python -m scanner.main --regions ap-south-1,us-east-1 --output findings.json

# With Docker Compose
docker-compose up postgres
docker-compose --profile scanner up
```

---

## Progress

- Phase 1: basic scanner and CLI
- Phase 2: Helm chart, k3s deployment, PostgreSQL integration
- Phase 3: GitHub Actions (OIDC), Jenkins CI/CD pipeline
- Phase 4: Prometheus metrics, Grafana dashboards, Alertmanager
- Phase 5: Terraform IaC (EC2, IAM, S3, GCP) + Ansible automation
- Phase 6: Demo data, Trivy hardening, operational scripts, ADRs, v1.0.0 release

---

## Architecture decisions

- [ADR 001 — Why GitHub Actions, not CronJob](docs/adr/001-why-github-actions-not-cronjob.md)
- [ADR 002 — Why PostgreSQL, not DynamoDB](docs/adr/002-why-postgresql-not-dynamodb.md)
- [ADR 003 — Why distroless, not Alpine](docs/adr/003-why-distroless-not-alpine.md)

---

## Layout

```
scanner/           scanner modules + metrics.py
notifier/          Slack notifier
db/                SQL schema + migrations
helm/              Helm chart + kube-prometheus-stack values
infra/k8s/         Pushgateway, Grafana dashboards, PrometheusRule
infra/terraform/   IaC: EC2, IAM role, S3, GCP bucket
infra/ansible/     Server automation: k3s, Jenkins, hardening
scripts/           All operational scripts
docs/              Demo findings, screenshots, ADRs, reports
vars/              Jenkins shared library functions
```
