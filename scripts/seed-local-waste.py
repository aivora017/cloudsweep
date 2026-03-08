#!/usr/bin/env python3
"""
Generate mock AWS resources for testing CloudSweep locally
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from moto import mock_ec2, mock_rds, mock_cloudwatch
import boto3

# Add scanner to path
sys.path.insert(0, '/home/sourav/cloudsweep')

from scanner.findings import (
    scan_idle_ec2,
    scan_orphaned_ebs,
    scan_unused_eips,
    scan_idle_rds,
    scan_old_snapshots
)


@mock_ec2
@mock_cloudwatch
@mock_rds
def generate_mock_waste():
    """Create mock resources"""
    region = 'ap-south-1'
    
    ec2 = boto3.client('ec2', region_name=region)
    cw = boto3.client('cloudwatch', region_name=region)
    rds = boto3.client('rds', region_name=region)
    
    print("Creating mock AWS resources...\n")
    
    print("1. Creating idle EC2 instances...")
    instance_ids = []
    for i in range(3):
        response = ec2.run_instances(
            ImageId='ami-12345678',
            MinCount=1,
            MaxCount=1,
            InstanceType='t2.micro',
            TagSpecifications=[{
                'ResourceType': 'instance',
                'Tags': [
                    {'Key': 'Name', 'Value': f'idle-instance-{i+1}'},
                    {'Key': 'Environment', 'Value': 'test'},
                ]
            }]
        )
        instance_id = response['Instances'][0]['InstanceId']
        instance_ids.append(instance_id)
        
        cw.put_metric_data(
            Namespace='AWS/EC2',
            MetricData=[{
                'MetricName': 'CPUUtilization',
                'Value': 2.0,
                'Unit': 'Percent',
                'Timestamp': datetime.now(timezone.utc),
                'Dimensions': [{'Name': 'InstanceId', 'Value': instance_id}]
            }]
        )
        print(f"   Created {instance_id} with 2% CPU")
    
    print("\n2. Creating orphaned EBS volumes...")
    for i in range(2):
        response = ec2.create_volume(
            AvailabilityZone=f'{region}a',
            Size=50,
            VolumeType='gp3',
            TagSpecifications=[{
                'ResourceType': 'volume',
                'Tags': [
                    {'Key': 'Name', 'Value': f'orphaned-volume-{i+1}'},
                ]
            }]
        )
        vol_id = response['VolumeId']
        print(f"   Created {vol_id} (50GB gp3, unattached)")
    
    print("\n3. Creating unused Elastic IP...")
    response = ec2.allocate_address(Domain='vpc')
    eip = response['PublicIp']
    print(f"   Created {eip} (not associated with any instance)")
    
    print("\n4. Creating idle RDS instance...")
    try:
        rds.create_db_instance(
            DBInstanceIdentifier='idle-mysql-db',
            Engine='mysql',
            DBInstanceClass='db.t3.micro',
            MasterUsername='admin',
            MasterUserPassword='TempPassword123',
            AllocatedStorage=20,
            Tags=[
                {'Key': 'Name', 'Value': 'test-db'},
                {'Key': 'Environment', 'Value': 'dev'}
            ]
        )
        print("   Created idle-mysql-db (db.t3.micro)")
        
        cw.put_metric_data(
            Namespace='AWS/RDS',
            MetricData=[{
                'MetricName': 'DatabaseConnections',
                'Value': 0.5,
                'Unit': 'Count',
                'Timestamp': datetime.now(timezone.utc),
                'Dimensions': [{'Name': 'DBInstanceIdentifier', 'Value': 'idle-mysql-db'}]
            }]
        )
    except Exception as e:
        print(f"   RDS mock limitation: {e}")
    
    print("\n5. Creating old snapshots...")
    for i in range(2):
        response = ec2.create_snapshot(
            VolumeId=list(ec2.describe_volumes()['Volumes'])[0]['VolumeId'] if list(ec2.describe_volumes()['Volumes']) else None,
            Description=f'Old snapshot {i+1}'
        )
        snap_id = response['SnapshotId']
        print(f"   Created {snap_id} (old snapshot)")
    
    print("\n" + "="*60)
    print("Mock resources created successfully!")
    print("="*60)
    
    return region


@mock_ec2
@mock_cloudwatch
@mock_rds
def scan_mock_resources():
    """Scan the mock resources and return findings"""
    region = 'ap-south-1'
    
    # First generate the resources
    generate_mock_waste()
    
    print("\n\nScanning for waste...\n")
    print("="*60)
    
    # Create a boto3 session
    session = boto3.Session(region_name=region)
    
    # Run all scan functions
    all_findings = []
    
    print("Running scan_idle_ec2...")
    findings_ec2 = scan_idle_ec2(session, region)
    all_findings.extend(findings_ec2)
    print(f"  Found {len(findings_ec2)} idle EC2 instances")
    
    print("Running scan_orphaned_ebs...")
    findings_ebs = scan_orphaned_ebs(session, region)
    all_findings.extend(findings_ebs)
    print(f"  Found {len(findings_ebs)} orphaned EBS volumes")
    
    print("Running scan_unused_eips...")
    findings_eips = scan_unused_eips(session, region)
    all_findings.extend(findings_eips)
    print(f"  Found {len(findings_eips)} unused EIPs")
    
    print("Running scan_idle_rds...")
    findings_rds = scan_idle_rds(session, region)
    all_findings.extend(findings_rds)
    print(f"  Found {len(findings_rds)} idle RDS instances")
    
    print("Running scan_old_snapshots...")
    findings_snapshots = scan_old_snapshots(session, region)
    all_findings.extend(findings_snapshots)
    print(f"  Found {len(findings_snapshots)} old snapshots")
    
    print("="*60)
    
    # Calculate totals
    total_usd = sum(f['monthly_cost_usd'] for f in all_findings)
    total_inr = sum(f['monthly_cost_inr'] for f in all_findings)
    
    result = {
        'findings': all_findings,
        'summary': {
            'total_findings': len(all_findings),
            'total_waste_usd': round(total_usd, 2),
            'total_waste_inr': round(total_inr, 2),
            'regions_scanned': [region],
            'scanned_at': datetime.now(timezone.utc).isoformat()
        }
    }
    
    return result


def main():
    """Run the scanning on mock resources"""
    try:
        print("\n")
        print("CloudSweep - Local Testing with Mocked AWS Resources")
        print("="*60)
        print()
        
        result = scan_mock_resources()
        
        # Print summary
        print("\n\nScan Summary")
        print("="*60)
        print(f"Total Findings: {result['summary']['total_findings']}")
        print(f"Total Waste (USD): ${result['summary']['total_waste_usd']:,.2f}")
        print(f"Total Waste (INR): ₹{result['summary']['total_waste_inr']:,.2f}")
        print(f"Scanned at: {result['summary']['scanned_at']}")
        print("="*60)
        
        # Print findings by type
        print("\nFindings by Resource Type:")
        print("-"*60)
        grouped = {}
        for finding in result['findings']:
            rtype = finding['resource_type']
            if rtype not in grouped:
                grouped[rtype] = []
            grouped[rtype].append(finding)
        
        for rtype, items in sorted(grouped.items()):
            waste_inr = sum(f['monthly_cost_inr'] for f in items)
            print(f"\n{rtype} ({len(items)} resources) — ₹{waste_inr:,.2f}/month")
            for item in items:
                print(f"  • {item['resource_id']} ({item['region']}) — {item['reason']}")
                print(f"    Cost: ₹{item['monthly_cost_inr']:,.2f}/month")
        
        # Save to file
        output_file = 'findings-mock.json'
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n\nFindings saved to: {output_file}")
        print("="*60)
        print("\nNext steps:")
        print("1. Review findings in findings-mock.json")
        print("2. Test Slack notification: SLACK_WEBHOOK_URL=xxx python scripts/test-slack-findings.py")
        print("3. Test database storage: DATABASE_URL=postgresql://... python scripts/store-findings.py")
        print()
        
    except Exception as e:
        print(f"Error during scan: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
