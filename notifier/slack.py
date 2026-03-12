import os
import httpx
from datetime import datetime
from typing import List, Dict, Optional


class SlackNotifier:

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv('SLACK_WEBHOOK_URL')
        if not self.webhook_url:
            raise ValueError("SLACK_WEBHOOK_URL environment variable not set")

    def send_digest(self, findings: List[Dict], summary: Dict):
        if not findings:
            msg = "CloudSweep Scan Complete - No waste detected!"
            self.send_message(msg)
            return

        grouped = {}
        for finding in findings:
            rtype = finding['resource_type']
            if rtype not in grouped:
                grouped[rtype] = []
            grouped[rtype].append(finding)

        total_waste_inr = summary['total_waste_inr']
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "CloudSweep Weekly Digest"
                }
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
        threshold = 50000
        if total_waste_inr > threshold:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*ALERT:* Waste exceeds ₹{threshold:,}/month"
                }
            })

        for rtype, items in sorted(grouped.items()):
            waste_inr = sum(f['monthly_cost_inr'] for f in items)
            lines = [
                f"*{rtype}* ({len(items)} resources) — ₹{waste_inr:,.2f}/mo"
            ]

            sorted_items = sorted(
                items,
                key=lambda x: x['monthly_cost_inr'],
                reverse=True
            )[:3]
            for item in sorted_items:
                cost = item['monthly_cost_inr']
                rid = item['resource_id']
                lines.append(f"  • `{rid}` — ₹{cost:,.2f}")

            if len(items) > 3:
                lines.append(f"  ... +{len(items) - 3} more")

            text = "\n".join(lines)

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text.strip()
                }
            })

        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        "Scanned at "
                        f"{datetime.now().strftime('%Y-%m-%d %H:%M IST')}"
                        " | <https://grafana.example.com|View Trends>"
                    )
                }
            ]
        })

        payload = {"blocks": blocks}
        self._send_payload(payload)

    def send_threshold_alert(
        self,
        findings: List[Dict],
        summary: Dict,
    ):
        total_waste_inr = summary['total_waste_inr']
        threshold = 50000

        if total_waste_inr > threshold:
            text = (
                "CRITICAL ALERT\n"
                f"Monthly AWS waste: ₹{total_waste_inr:,.2f} "
                f"(threshold: ₹{threshold:,})\n"
                f"{summary['total_findings']} resources identified for cleanup"
            )
            self.send_message(text)

    def send_message(self, text: str):
        payload = {
            "text": text
        }
        self._send_payload(payload)

    def _send_payload(self, payload: Dict):
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(self.webhook_url, json=payload)
                response.raise_for_status()
        except httpx.HTTPError as e:
            print(f"Error sending Slack notification: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
