#!/usr/bin/env python3
"""
Test Slack notification with sample findings
"""

import sys
import json
import os

sys.path.insert(0, '/home/sourav/cloudsweep')

from notifier.slack import SlackNotifier


def create_sample_findings():
    """Create sample findings for testing"""
    return [
        {
            'resource_id': 'i-0a1b2c3d4e5f6g7h8',
            'resource_type': 'EC2',
            'region': 'ap-south-1',
            'reason': 'CPU avg 2.3% over 7 days',
            'monthly_cost_usd': 7.38,
            'monthly_cost_inr': 678.51,
            'tags': {'Name': 'idle-instance-1', 'Environment': 'test'},
            'detected_at': '2026-03-07T05:30:00+00:00'
        },
        {
            'resource_id': 'i-1b2c3d4e5f6g7h8i9',
            'resource_type': 'EC2',
            'region': 'us-east-1',
            'reason': 'CPU avg 1.8% over 7 days',
            'monthly_cost_usd': 8.50,
            'monthly_cost_inr': 781.49,
            'tags': {'Name': 'idle-instance-2', 'Owner': 'devops'},
            'detected_at': '2026-03-07T05:30:00+00:00'
        },
        {
            'resource_id': 'vol-0x1y2z3a4b5c6d7e8',
            'resource_type': 'EBS',
            'region': 'ap-south-1',
            'reason': '50GB gp3 unattached',
            'monthly_cost_usd': 4.00,
            'monthly_cost_inr': 367.76,
            'tags': {'Name': 'orphaned-volume-1'},
            'detected_at': '2026-03-07T05:30:00+00:00'
        },
        {
            'resource_id': 'vol-1y2z3a4b5c6d7e8f9',
            'resource_type': 'EBS',
            'region': 'ap-south-1',
            'reason': '100GB gp3 unattached',
            'monthly_cost_usd': 8.00,
            'monthly_cost_inr': 735.52,
            'tags': {'Name': 'orphaned-volume-2'},
            'detected_at': '2026-03-07T05:30:00+00:00'
        },
        {
            'resource_id': '203.0.113.42',
            'resource_type': 'EIP',
            'region': 'ap-south-1',
            'reason': 'Unassociated (costs $0.005/hour when unused)',
            'monthly_cost_usd': 3.65,
            'monthly_cost_inr': 335.58,
            'tags': {},
            'detected_at': '2026-03-07T05:30:00+00:00'
        }
    ]


def main():
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    
    if not webhook_url:
        print("Error: SLACK_WEBHOOK_URL environment variable not set")
        print("\nUsage:")
        print("  export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL")
        print("  python scripts/test-findings-slack.py")
        sys.exit(1)
    
    print("Testing Slack notification with sample findings...\n")
    
    # Create sample findings
    findings = create_sample_findings()
    
    # Create summary
    summary = {
        'total_findings': len(findings),
        'total_waste_usd': sum(f['monthly_cost_usd'] for f in findings),
        'total_waste_inr': sum(f['monthly_cost_inr'] for f in findings),
        'regions_scanned': ['ap-south-1', 'us-east-1'],
        'scanned_at': '2026-03-07T05:30:00+00:00'
    }
    
    print(f"Sample findings summary:")
    print(f"  - Total findings: {summary['total_findings']}")
    print(f"  - Total waste: ₹{summary['total_waste_inr']:,.2f}/month")
    print(f"  - Regions: {', '.join(summary['regions_scanned'])}")
    
    try:
        notifier = SlackNotifier(webhook_url)
        print("\nSending to Slack...")
        notifier.send_digest(findings, summary)
        print("Success! Check your Slack channel for the message.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
