import os
import time
from prometheus_client import (
    CollectorRegistry,
    Gauge,
    Histogram,
    push_to_gateway,
)

PUSHGATEWAY_URL = os.getenv('PUSHGATEWAY_URL', 'http://pushgateway:9091')
JOB_NAME = 'cloudsweep_scanner'


def push_metrics(all_findings, summary, scan_duration_seconds):
    """Push scan metrics to Prometheus Pushgateway."""
    registry = CollectorRegistry()

    waste_total = Gauge(
        'cloudsweep_waste_total_inr',
        'Monthly waste in INR by resource type and region',
        ['resource_type', 'region'],
        registry=registry,
    )

    findings_total = Gauge(
        'cloudsweep_findings_total',
        'Number of active waste findings by resource type',
        ['resource_type'],
        registry=registry,
    )

    scan_duration = Gauge(
        'cloudsweep_scan_duration_seconds',
        'Time taken to complete the scan in seconds',
        registry=registry,
    )

    last_scan = Gauge(
        'cloudsweep_last_scan_timestamp',
        'Unix timestamp of the last completed scan',
        registry=registry,
    )

    # Aggregate waste and counts by resource_type + region
    waste_by_type_region = {}
    count_by_type = {}

    for finding in all_findings:
        resource_type = finding.get('resource_type', 'unknown')
        region = finding.get('region', 'unknown')
        cost_inr = finding.get('monthly_cost_inr', 0)

        key = (resource_type, region)
        waste_by_type_region[key] = waste_by_type_region.get(key, 0) + cost_inr
        count_by_type[resource_type] = count_by_type.get(resource_type, 0) + 1

    for (resource_type, region), cost in waste_by_type_region.items():
        waste_total.labels(resource_type=resource_type, region=region).set(cost)

    for resource_type, count in count_by_type.items():
        findings_total.labels(resource_type=resource_type).set(count)

    scan_duration.set(scan_duration_seconds)
    last_scan.set(time.time())

    push_to_gateway(PUSHGATEWAY_URL, job=JOB_NAME, registry=registry)
