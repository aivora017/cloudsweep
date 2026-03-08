# CloudSweep Project Phases

## Phase 1: Scanner Engine — DONE ✓

- [x] Monorepo structure (scanner/, notifier/, db/, tests/, scripts/)
- [x] 5 scan functions (EC2 idle, EBS orphaned, EIP unused, RDS idle, Snapshots)
- [x] Pricing module (CSV-based, USD→INR conversion)
- [x] Main CLI orchestrator (--regions, --output flags)
- [x] Slack notifier (weekly digest + threshold alerts)
- [x] PostgreSQL schema (scan_runs, findings, active_waste view)
- [x] Docker multi-stage build (<80MB final image)
- [x] docker-compose.yml (local dev with postgres)
- [x] Bash utilities (run-scan.sh, export-csv.sh)
- [x] Unit tests (7 tests, 80% coverage, all passing)
- [x] GitHub repo with clean structure
- [x] Production-grade code (no fluff, human-written)

**Status:** COMPLETE — Ready for Phase 2

---

## Phase 2: Data Layer — IN PROGRESS

- [ ] PostgreSQL as K8s StatefulSet with PVC
- [ ] Helm chart (scanner CronJob, postgres StatefulSet, services)
- [ ] Migration job hook for database schema
- [ ] Resolved finding tracking (mark old findings as resolved)
- [ ] 12-week waste trend view and queries
- [ ] CronJob schedule (Monday 2AM UTC = 7:30AM IST)
- [ ] values.yaml with configurable thresholds
- [ ] kubectl integration testing
- [ ] Pre-install Helm hooks for migrations

**Target:** Days 7-10

---

## Phase 3: CI/CD — NOT STARTED

- [ ] GitHub Actions: scheduled-scan.yml (weekly Monday 2AM)
- [ ] GitHub Actions: pr-checks.yml (pytest + flake8 + bandit + hadolint)
- [ ] AWS OIDC for GitHub Actions (no long-lived keys)
- [ ] Jenkins pipeline (flake8 → bandit → pytest → docker build → helm)
- [ ] Jenkins shared library (pythonBuild, dockerPush, helmDeploy)
- [ ] Multi-branch Jenkins (feature/* → test, main → deploy)
- [ ] BuildKit Docker layer caching
- [ ] Post-deploy smoke tests

**Target:** Days 11-16

---

## Phase 4: Monitoring — NOT STARTED

- [ ] Prometheus metrics emission (scanner/metrics.py)
- [ ] cloudsweep_waste_total_inr gauge
- [ ] cloudsweep_findings_total counter
- [ ] cloudsweep_scan_duration_seconds histogram
- [ ] ServiceMonitor CRD for auto-discovery
- [ ] Grafana dashboards (Overview, Breakdown, Health)
- [ ] Alerts (WasteThresholdCrossed, ScanStale)

**Target:** Days 17-22

---

## Phase 5: Infrastructure as Code — NOT STARTED

- [ ] Terraform: IAM role with least-privilege policy
- [ ] Terraform: S3 bucket for reports (90-day lifecycle)
- [ ] Terraform: GCP Cloud Storage for cross-cloud backup
- [ ] Terraform: EC2 t2.micro for k3s + Grafana + PostgreSQL
- [ ] Terraform: Remote state (S3 + DynamoDB lock)
- [ ] Ansible: bootstrap-server role (Docker, Python, curl)
- [ ] Ansible: install-k3s role
- [ ] Ansible: configure-aws role
- [ ] Ansible: harden-server role (UFW, fail2ban)
- [ ] Bash: infra-up.sh (terraform → ansible → helm one-shot)

**Target:** Days 23-28

---

## Phase 6: Polish & Demo — NOT STARTED

- [ ] Seed script for demo (3 idle EC2s, 2 orphaned EBS, 1 unused EIP)
- [ ] Cost report PDF generator
- [ ] Bulk resolve script
- [ ] Trivy CVE scanning in GitHub Actions
- [ ] Network policies for scanner pod
- [ ] Architecture diagrams in README
- [ ] ADRs (Architecture Decision Records)
- [ ] Real findings.json in docs/
- [ ] Grafana screenshot in README
- [ ] Slack screenshot in README

**Target:** Days 29-35

---

## Metrics

| Phase | Status | Tests | Coverage | Code LOC |
|-------|--------|-------|----------|----------|
| 1 | DONE | 7/7 ✓ | 80% | 693 |
| 2 | IN PROGRESS | - | - | - |
| 3 | NOT STARTED | - | - | - |
| 4 | NOT STARTED | - | - | - |
| 5 | NOT STARTED | - | - | - |
| 6 | NOT STARTED | - | - | - |

---

## Latest Updates

- **2026-03-08**: Phase 1 complete. All 7 tests passing. GitHub repo live. LinkedIn post ready.
