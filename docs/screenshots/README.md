# Screenshots

Screenshots are captured after running the demo scan.

## How to capture

```bash
# 1. Seed demo resources (requires real AWS account)
./scripts/seed-demo-waste.sh --region ap-south-1

# 2. Run the scan
python -m scanner.main --regions ap-south-1 --slack --output docs/demo-findings.json

# 3. Port-forward Grafana
kubectl port-forward svc/kube-prometheus-stack-grafana 3000:80 -n monitoring
# Open http://localhost:3000  — admin / cloudsweep-admin

# 4. Take screenshots and save here:
#    grafana-waste.png     — CloudSweep Waste Overview dashboard
#    grafana-breakdown.png — Resource Breakdown dashboard
#    grafana-health.png    — Scan Health dashboard
#    slack-digest.png      — Slack alert with ₹ total
```

## Expected content

### grafana-waste.png
- Total waste gauge showing ₹2,660/month
- 12-week trend line (flat or rising)
- Breakdown by type: EC2 ₹2,092 | EIP ₹301 | EBS ₹267

### grafana-breakdown.png
- Bar chart of top wasteful resources
- Region heatmap (ap-south-1 highlighted)

### grafana-health.png
- Last scan: today's date
- Scan duration: ~8s
- Scan frequency: weekly

### slack-digest.png
- Slack message showing 6 findings
- Total waste: ₹2,660/month
- Breakdown table by resource type
