# ADR 001 — Why GitHub Actions for scheduled scans, not a bare Kubernetes CronJob

**Date:** 2026-03-26
**Status:** Accepted

---

## Context

CloudSweep needs to scan AWS accounts on a weekly schedule and notify
stakeholders of waste. Two options were considered:

1. **GitHub Actions scheduled workflow** (`on: schedule: cron`)
2. **Kubernetes CronJob** running directly on the k3s cluster

## Decision

Use GitHub Actions for the weekly production scan (`scheduled-scan.yml`)
while keeping the Kubernetes CronJob as the in-cluster fallback for
self-hosted or air-gapped deployments.

## Reasons

### AWS credential safety
GitHub Actions uses **OIDC** to assume an IAM role without storing long-lived
access keys anywhere. A Kubernetes CronJob would require either a
`Secret` containing static credentials, an IRSA binding (EKS-only), or
EC2 instance metadata — all of which add operational complexity or risk.

### Zero infrastructure dependency for the scan itself
The scan runs on GitHub-hosted runners. If the k3s server is down for
maintenance, the weekly scan still fires. Decoupling the scan scheduler from
the scanned infrastructure prevents a single point of failure.

### Audit trail for free
Every GitHub Actions run produces a timestamped log, artifact (findings.json),
and status badge. Kubernetes CronJob logs require a separate log aggregation
setup (Loki, CloudWatch, etc.) to achieve the same visibility.

### Simpler OIDC setup than alternatives
AWS OIDC + GitHub Actions is a well-documented pattern with a first-party
action (`configure-aws-credentials@v4`). Setting up Workload Identity for
a Kubernetes CronJob would require EKS or a custom OIDC provider, neither
of which is present in this k3s deployment.

## Trade-offs accepted

- **Vendor coupling:** The scheduled scan depends on GitHub's infrastructure.
  Mitigated by the Kubernetes CronJob which runs independently.
- **Limited concurrency control:** GitHub Actions has queue/concurrency
  semantics that differ from Kubernetes. We use `concurrency: cancel-in-progress`
  to avoid duplicate scans.
- **Cold-start latency:** Runner provisioning adds ~30s versus a CronJob that
  starts immediately. Acceptable for a weekly cadence.

## Consequences

- `scheduled-scan.yml` is the authoritative weekly scan.
- `helm/cloudsweep/templates/cronjob.yaml` remains in the chart as a
  self-hosted deployment path (Helm users who don't use GitHub Actions).
- Adding a new region requires updating both the workflow env and the Helm
  values file.
