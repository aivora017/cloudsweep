#!/usr/bin/env python3
"""
test-findings-db.py — Test database storage with sample findings

Stores sample findings in PostgreSQL without requiring real AWS scan.
Useful for testing database connectivity and schema before production.
"""

import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, '/home/sourav/cloudsweep')

from db.manager import DatabaseManager


def create_sample_findings():
    """Create realistic sample findings for testing"""
    return [
        {
            'resource_id': 'i-0a1b2c3d4e5f6g7h8',
            'resource_type': 'EC2',
            'region': 'ap-south-1',
            'reason': 'CPU avg 2.3% over 7 days',
            'monthly_cost_usd': 7.38,
            'monthly_cost_inr': 678.51,
            'tags': {'Name': 'idle-instance-1', 'Environment': 'test'},
            'detected_at': datetime.now(timezone.utc).isoformat()
        },
        {
            'resource_id': 'i-1b2c3d4e5f6g7h8i9',
            'resource_type': 'EC2',
            'region': 'us-east-1',
            'reason': 'CPU avg 1.8% over 7 days',
            'monthly_cost_usd': 8.50,
            'monthly_cost_inr': 781.49,
            'tags': {'Name': 'idle-instance-2', 'Owner': 'devops'},
            'detected_at': datetime.now(timezone.utc).isoformat()
        },
        {
            'resource_id': 'vol-0x1y2z3a4b5c6d7e8',
            'resource_type': 'EBS',
            'region': 'ap-south-1',
            'reason': '50GB gp3 unattached',
            'monthly_cost_usd': 4.00,
            'monthly_cost_inr': 367.76,
            'tags': {'Name': 'orphaned-volume-1'},
            'detected_at': datetime.now(timezone.utc).isoformat()
        },
        {
            'resource_id': 'vol-1y2z3a4b5c6d7e8f9',
            'resource_type': 'EBS',
            'region': 'ap-south-1',
            'reason': '100GB gp3 unattached',
            'monthly_cost_usd': 8.00,
            'monthly_cost_inr': 735.52,
            'tags': {'Name': 'orphaned-volume-2'},
            'detected_at': datetime.now(timezone.utc).isoformat()
        },
        {
            'resource_id': '203.0.113.42',
            'resource_type': 'EIP',
            'region': 'ap-south-1',
            'reason': 'Unassociated (costs $0.005/hour when unused)',
            'monthly_cost_usd': 3.65,
            'monthly_cost_inr': 335.58,
            'tags': {},
            'detected_at': datetime.now(timezone.utc).isoformat()
        }
    ]


def main():
    db_url = os.getenv('DATABASE_URL')
    
    if not db_url:
        print("Error: DATABASE_URL environment variable not set")
        print("\nUsage:")
        print("  export DATABASE_URL=postgresql://cloudsweep:password@localhost:5432/cloudsweep")
        print("  python scripts/test-findings-db.py")
        print("\nOr use docker-compose:")
        print("  docker-compose up postgres -d")
        print("  export DATABASE_URL=postgresql://cloudsweep:cloudsweep_dev@localhost:5432/cloudsweep")
        print("  python scripts/test-findings-db.py")
        sys.exit(1)
    
    print("Testing database storage with sample findings...\n")
    
    try:
        # Connect to database
        db = DatabaseManager(db_url)
        print("Connected to database successfully!")
        
        # Create sample findings
        findings = create_sample_findings()
        regions = ['ap-south-1', 'us-east-1']
        
        print(f"\nInserting test data:")
        print(f"  - Region list: {regions}")
        print(f"  - Findings count: {len(findings)}")
        print(f"  - Total waste: ₹{sum(f['monthly_cost_inr'] for f in findings):,.2f}/month")
        
        # Insert scan run
        scan_run_id = db.insert_scan_run(regions, findings)
        print(f"\nInserted scan_run with ID: {scan_run_id}")
        
        # Insert findings
        db.insert_findings(scan_run_id, findings)
        print(f"Inserted {len(findings)} findings")
        
        # Verify data was stored
        with db.get_connection() as conn:
            cur = conn.cursor()
            
            # Check scan_runs table
            cur.execute("SELECT id, regions, total_findings, total_waste_inr FROM scan_runs WHERE id = %s", (scan_run_id,))
            row = cur.fetchone()
            if row:
                print(f"\nVerification - scan_runs table:")
                print(f"  ID: {row[0]}")
                print(f"  Regions: {row[1]}")
                print(f"  Total findings: {row[2]}")
                print(f"  Total waste (INR): ₹{row[3]:,.2f}")
            
            # Check findings table
            cur.execute("SELECT COUNT(*), SUM(monthly_cost_inr) FROM findings WHERE scan_run_id = %s", (scan_run_id,))
            count, total = cur.fetchone()
            print(f"\nVerification - findings table:")
            print(f"  Stored findings: {count}")
            print(f"  Sum of waste: ₹{total:,.2f}")
            
            # Show active_waste view
            cur.execute("""
                SELECT resource_type, region, COUNT(*) as count, SUM(monthly_cost_inr) as waste_inr
                FROM findings
                WHERE scan_run_id = %s AND resolved_at IS NULL
                GROUP BY resource_type, region
                ORDER BY waste_inr DESC
            """, (scan_run_id,))
            
            print(f"\nActive waste summary:")
            for row in cur.fetchall():
                print(f"  {row[0]} in {row[1]}: {row[2]} resources, ₹{row[3]:,.2f}/month")
        
        print("\nSuccess! Database storage test completed.")
        print(f"\nScan run ID for reference: {scan_run_id}")
        print("You can query this data later using:")
        print(f"  SELECT * FROM findings WHERE scan_run_id = {scan_run_id};")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
