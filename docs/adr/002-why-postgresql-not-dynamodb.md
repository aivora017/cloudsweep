# ADR 002 — Why PostgreSQL for findings storage, not DynamoDB

**Date:** 2026-03-26
**Status:** Accepted

---

## Context

CloudSweep stores scan runs, findings, and trend data that managers query
over a 12-week window. Two storage backends were considered:

1. **PostgreSQL** (self-hosted on k3s via StatefulSet)
2. **AWS DynamoDB** (managed, serverless, same cloud as the scanned resources)

## Decision

Use PostgreSQL.

## Reasons

### Aggregation and trend queries
The core manager-facing feature is "show me total waste over 12 weeks broken
down by resource type." This requires:

```sql
SELECT DATE(scanned_at), resource_type, SUM(monthly_cost_inr)
FROM scan_runs JOIN findings ON ...
WHERE scanned_at >= NOW() - INTERVAL '12 weeks'
GROUP BY 1, 2;
```

DynamoDB is a key-value store. Running this query on DynamoDB requires a
full table scan + application-side aggregation or a DynamoDB Stream feeding
into Athena/Redshift — significant added infrastructure.

### Views and functions in the schema
`waste_trend_12w`, `active_waste`, and `resolve_missing_findings()` are SQL
primitives that encapsulate business logic in the database layer.
DynamoDB has no equivalent concept.

### Cost at this scale
At roughly 300 findings/week and 12 weeks of retention (~3,600 rows total),
a `db.t3.micro` RDS instance ($12/month) or the self-hosted StatefulSet
($0 marginal cost) are both cheaper than DynamoDB on-demand pricing
($1.25/million writes + $0.25/million reads), which doesn't apply at this
scale but would at enterprise volume.

### No vendor lock-in for the data layer
Keeping the database inside the k3s cluster means the entire stack is
portable to any cloud, on-premises, or local environment without changing
the schema or queries.

### Existing Helm chart support
PostgreSQL fits naturally into the Helm chart as a StatefulSet + Service.
DynamoDB would require external access and IAM permissions even for
development and testing, adding friction to `docker-compose up` and CI.

## Trade-offs accepted

- **Operational burden:** PostgreSQL requires a persistent volume, backup
  strategy, and occasional tuning. Mitigated by the small data volume and
  the automated `rotate-credentials.sh` script.
- **No auto-scaling:** A heavy burst of scan activity could slow down queries.
  Acceptable given the weekly batch cadence and <10,000 rows total expected.
- **Single-AZ:** The StatefulSet has no automatic failover. For production the
  recommendation is to use RDS Multi-AZ — but that is out of scope for this
  project which targets a single t2.micro server.

## Consequences

- `db/migrations/001_init.sql` defines the full schema including views and
  a PL/pgSQL function.
- `scripts/cost-report.sh` queries the `waste_trend_12w` view directly.
- Future: if the project moves to multi-account scanning at scale, consider
  an S3 + Athena approach as a read replica for analytics while keeping
  PostgreSQL for real-time writes.
