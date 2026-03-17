# Phase 3 Proof of Done

## Workflow files

**pr-checks.yml**
Runs on every pull request to main. Steps: checkout, install dependencies,
flake8 (style), bandit (security), pytest with 85% coverage gate, hadolint
(Dockerfile lint). The PR cannot merge if any step fails.

**scheduled-scan.yml**
Runs every Monday at 2AM UTC (7:30AM IST) via cron schedule. Also has a
manual trigger button (workflow_dispatch). Uses AWS OIDC to assume an IAM
role — no long-lived keys stored anywhere. Runs the scanner, then uploads
findings.json as a build artifact retained for 30 days.

## Jenkins pipeline stages

1. **Lint** — flake8 checks style, bandit checks for security issues. Fails
   fast on any violation.
2. **Test** — installs all dependencies, runs pytest with coverage report.
   Build fails if coverage drops below 85%.
3. **Build and Push** — only on main branch. Builds Docker image with BuildKit
   cache and pushes to ghcr.io with commit SHA tag.
4. **Deploy** — only on main branch. Runs helm upgrade with --atomic flag so
   Kubernetes automatically rolls back if health checks fail.

## Branch strategy

- `feature/*` branches: only Lint and Test stages run
- `main` branch: full pipeline runs — Lint, Test, Build and Push, Deploy
- post-success smoke test on main: queries PostgreSQL to verify scanner
  connected and wrote findings

## AWS OIDC

GitHub Actions uses OpenID Connect to request a short-lived token from AWS
instead of using stored access keys. GitHub sends a signed JWT to AWS STS,
which validates it against the configured IAM role trust policy and returns
temporary credentials that expire after the workflow finishes. This means
there are no long-lived secrets to rotate, leak, or accidentally commit.

## Flake8 failure proof

Deliberate error introduced: `import sys` added to scanner/main.py (unused).

```
=== flake8 ===
scanner/main.py:5:1: F401 'sys' imported but unused
FAIL: flake8

=== bandit ===
PASS: bandit

=== pytest ===
PASS: pytest

==============================
Results: 2 passed, 1 failed
==============================
```

After removing the unused import:

```
=== flake8 ===
PASS: flake8

=== bandit ===
PASS: bandit

=== pytest ===
Required test coverage of 85% reached. Total coverage: 86.48%
40 passed, 24 warnings in 5.15s
PASS: pytest

==============================
Results: 3 passed, 0 failed
==============================
```
