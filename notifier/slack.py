import os
import httpx
from datetime import datetime


class SlackNotifier:

    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url or os.getenv('SLACK_WEBHOOK_URL')
        if not self.webhook_url:
            raise ValueError("SLACK_WEBHOOK_URL environment variable not set")

    def send_digest(self, findings, summary):
        if not findings:
            self.send_message("CloudSweep Scan Complete - No waste detected!")
            return

        grouped = {}
        for finding in findings:
            rtype = finding['resource_type']
            grouped.setdefault(rtype, []).append(finding)

        total_waste_inr = summary['total_waste_inr']
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "CloudSweep Weekly Digest"}
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Total Monthly Waste:* ₹{total_waste_inr:,.2f}\n"
                        f"*Findings:* {summary['total_findings']}\n"
                        f"*Scanned:* {', '.join(summary['regions_scanned'])}"
                    )
                }
            }
        ]

        if total_waste_inr > 50000:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*ALERT:* Waste exceeds ₹50,000/month"}
            })

        for rtype, items in sorted(grouped.items()):
            waste_inr = sum(f['monthly_cost_inr'] for f in items)
            lines = [f"*{rtype}* ({len(items)} resources) — ₹{waste_inr:,.2f}/mo"]

            for item in sorted(items, key=lambda x: x['monthly_cost_inr'], reverse=True)[:3]:
                lines.append(f"  • `{item['resource_id']}` — ₹{item['monthly_cost_inr']:,.2f}")

            if len(items) > 3:
                lines.append(f"  ... +{len(items) - 3} more")

            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(lines)}
            })

        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"Scanned at {datetime.now().strftime('%Y-%m-%d %H:%M IST')} | <https://grafana.example.com|View Trends>"
            }]
        })

        self._send_payload({"blocks": blocks})

    def send_threshold_alert(self, findings, summary):
        total_waste_inr = summary['total_waste_inr']
        if total_waste_inr > 50000:
            text = (
                f"CRITICAL ALERT\n"
                f"Monthly AWS waste: ₹{total_waste_inr:,.2f} (threshold: ₹50,000)\n"
                f"{summary['total_findings']} resources identified for cleanup"
            )
            self.send_message(text)

    def send_message(self, text):
        self._send_payload({"text": text})

    def _send_payload(self, payload):
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(self.webhook_url, json=payload)
                response.raise_for_status()
        except httpx.HTTPError as e:
            print(f"Error sending Slack notification: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
