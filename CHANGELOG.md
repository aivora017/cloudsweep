# Changelog

## v1.0.0 — 2026-03-26

First production-ready release of CloudSweep.

### Features

**Phase 1 — Scanner**
- Scan EC2 (idle CPU), EBS (unattached), EIP (unused), RDS (low connections), EBS snapshots (old)
- INR + USD pricing using live exchange rate
- JSON output + CLI (`--regions`, `--output`, `--slack`, `--dry-run`)

**Phase 2 — Kubernetes**
- Helm chart: CronJob scanner, PostgreSQL StatefulSet, pre-install migration job
- NetworkPolicy: scanner egress-only (AWS:443, PostgreSQL:5432, Pushgateway:9091)
- Kubernetes Secrets for all credentials — nothing in ConfigMaps
- k3s single-node deployment

**Phase 3 — CI/CD**
- GitHub Actions: `pr-checks.yml` (flake8, bandit, pytest 85%, Dockerfile lint, Trivy)
- GitHub Actions: `scheduled-scan.yml` (weekly, OIDC — zero stored keys)
- Jenkins pipeline: Lint → Test → Build & Push → Deploy (Helm `--atomic`)
- Jenkins shared library in `vars/`

**Phase 4 — Monitoring**
- Prometheus metrics via Pushgateway (4 metrics with resource_type + region labels)
- 3 Grafana dashboards auto-provisioned via ConfigMap: Waste Overview, Resource Breakdown, Scan Health
- Alertmanager: Slack alerts for waste > ₹50,000 or scan missing > 8 days
- `kube-prometheus-stack` Helm chart with all components

**Phase 5 — Infrastructure as Code**
- Terraform modules: `iam-scanner-role` (least-privilege), `ec2-server` (t2.micro + EIP), `s3-reports` (90-day lifecycle), `gcp-backup` (always-free GCS)
- S3 + DynamoDB remote state backend
- Ansible roles: `bootstrap-server`, `install-k3s`, `install-jenkins`, `configure-aws`, `harden-server` (UFW + fail2ban)
- `scripts/infra-up.sh` — full stack in one command (~8 min)
- `scripts/infra-down.sh` — full teardown

**Phase 6 — Demo & Hardening**
- `scripts/seed-demo-waste.sh` — creates real demo waste resources + cleanup
- `docs/demo-findings.json` — real scan results with ₹ amounts
- Trivy CVE scan added to PR checks (fails on CRITICAL/HIGH)
- `scripts/verify-iam.sh` — confirms read-only via `simulate-principal-policy`
- `scripts/rotate-credentials.sh` — zero-downtime DB password rotation
- `scripts/bulk-resolve.sh` — mark findings resolved after cleanup sprint
- `scripts/cost-report.sh` — weekly CSV from `waste_trend_12w` view
- 3 Architecture Decision Records (ADRs)
- GitHub issue template + PR template
- README: architecture diagram, 5-minute quickstart, demo findings table, load test results

### Security

- Distroless runtime image (`gcr.io/distroless/python3-debian12:nonroot`)
- No shell, no root, no long-lived AWS keys anywhere
- IAM explicit deny on all mutating actions
- Server: UFW + fail2ban + key-only SSH + root login disabled

### Proof of done

```
helm install cloudsweep ./helm/cloudsweep   # works on clean k3s in <5 min
./scripts/verify-iam.sh                     # all write actions: implicitDeny
aws iam simulate-principal-policy ...       # ec2:TerminateInstances → denied
```
