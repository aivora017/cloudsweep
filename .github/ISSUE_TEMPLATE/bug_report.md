---
name: Bug report
about: Report a scanner error, wrong pricing, or dashboard issue
title: "[BUG] "
labels: bug
assignees: aivora017
---

## What happened?

<!-- A clear, concise description of the bug. -->

## Expected behaviour

<!-- What did you expect to happen? -->

## Steps to reproduce

1.
2.
3.

## Scan output / error message

```
paste scanner output or error here
```

## Environment

| Field | Value |
|-------|-------|
| CloudSweep version / commit | |
| Python version | |
| AWS region(s) scanned | |
| Deployment method | Helm / docker-compose / local |
| k3s / Kubernetes version | |

## findings.json snippet (if relevant)

```json
{
  "resource_id": "...",
  "resource_type": "...",
  "reason": "...",
  "monthly_cost_inr": 0
}
```

## Additional context

<!-- Screenshots, Grafana dashboard state, Prometheus metrics, etc. -->
