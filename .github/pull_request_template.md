## What does this PR do?

<!-- One paragraph summary. Link the issue it resolves if applicable. -->

Closes #

## Type of change

- [ ] Bug fix
- [ ] New feature / scanner module
- [ ] Refactor / tech debt
- [ ] Docs / ADR
- [ ] CI/CD / infra

## Changes

<!-- Bullet list of the key files changed and why. -->

-
-

## Testing

- [ ] `pytest tests/` passes locally (`pytest --cov=scanner --cov-fail-under=85`)
- [ ] `flake8 scanner notifier db` clean
- [ ] `bandit -r scanner notifier` clean
- [ ] Trivy scan shows no new CRITICAL/HIGH CVEs (CI enforces this)
- [ ] If helm templates changed: `helm template cloudsweep ./helm/cloudsweep` renders without error

## For scanner changes

- [ ] Tested against mock findings (`USE_MOCK_FINDINGS=true`)
- [ ] Tested against real AWS (or noted why not)
- [ ] Pricing logic verified against AWS pricing page

## Screenshots / output (if relevant)

<!-- Grafana dashboard, Slack message, scan output, etc. -->

## Checklist

- [ ] No credentials, API keys, or connection strings in committed files
- [ ] No `print()` statements left in production code (use `click.echo` or logging)
- [ ] New scripts are `chmod +x` and have a usage comment at the top
