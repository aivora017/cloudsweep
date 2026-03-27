from datetime import datetime, timezone, timedelta
import os
from scanner.pricing import (
    EIP_MONTHLY_COST,
    convert_usd_to_inr,
    get_ec2_cost,
    get_ebs_cost,
    get_rds_cost,
    get_snapshot_cost
)


def is_free_tier_eligible(vol):
    created_at = vol.get('CreateTime')
    if not created_at:
        return False
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - created_at).days
    return age_days < 365


def scan_idle_ec2(session, region):
    ec2 = session.client('ec2', region_name=region)
    cw = session.client('cloudwatch', region_name=region)
    findings = []

    cpu_idle_threshold = float(os.getenv('CPU_IDLE_THRESHOLD', '5'))

    response = ec2.describe_instances(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
    )

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            instance_type = instance['InstanceType']

            metrics = cw.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=datetime.now(timezone.utc) - timedelta(days=7),
                EndTime=datetime.now(timezone.utc),
                Period=604800,
                Statistics=['Average']
            )

            datapoints = metrics.get('Datapoints', [])
            avg_cpu = datapoints[0]['Average'] if datapoints else 0

            if avg_cpu < cpu_idle_threshold:
                cost = get_ec2_cost(instance_type)
                tags = {t['Key']: t['Value'] for t in instance.get('Tags', [])}
                findings.append({
                    'resource_id': instance_id,
                    'resource_type': 'EC2',
                    'region': region,
                    'reason': f'CPU avg {avg_cpu:.1f}% over 7 days (threshold: {cpu_idle_threshold:.1f}%)',
                    'monthly_cost_usd': cost,
                    'monthly_cost_inr': convert_usd_to_inr(cost),
                    'tags': tags,
                    'detected_at': datetime.now(timezone.utc).isoformat()
                })

    return findings


def scan_orphaned_ebs(session, region):
    ec2 = session.client('ec2', region_name=region)
    findings = []

    response = ec2.describe_volumes(
        Filters=[{'Name': 'status', 'Values': ['available']}]
    )

    for vol in response['Volumes']:
        vol_type = vol.get('VolumeType', 'gp2')

        # skip free-tier eligible volumes (<=30GB, account under 12 months old)
        if vol['Size'] <= 30 and is_free_tier_eligible(vol):
            continue

        cost = get_ebs_cost(vol['Size'], vol_type)
        tags = {t['Key']: t['Value'] for t in vol.get('Tags', [])}
        findings.append({
            'resource_id': vol['VolumeId'],
            'resource_type': 'EBS',
            'region': region,
            'reason': f'{vol["Size"]}GB {vol_type} unattached',
            'monthly_cost_usd': cost,
            'monthly_cost_inr': convert_usd_to_inr(cost),
            'tags': tags,
            'detected_at': datetime.now(timezone.utc).isoformat()
        })

    return findings


def scan_unused_eip(session, region):
    ec2 = session.client('ec2', region_name=region)
    findings = []

    for eip in ec2.describe_addresses()['Addresses']:
        if (
            not eip.get('InstanceId')
            and not eip.get('NetworkInterfaceId')
            and not eip.get('AssociationId')
        ):
            findings.append({
                'resource_id': eip['PublicIp'],
                'resource_type': 'EIP',
                'region': region,
                'reason': 'Unassociated (costs $0.005/hour when unused)',
                'monthly_cost_usd': EIP_MONTHLY_COST,
                'monthly_cost_inr': convert_usd_to_inr(EIP_MONTHLY_COST),
                'tags': {},
                'detected_at': datetime.now(timezone.utc).isoformat()
            })

    return findings


def scan_underused_rds(session, region):
    rds = session.client('rds', region_name=region)
    cw = session.client('cloudwatch', region_name=region)
    findings = []

    try:
        response = rds.describe_db_instances()
    except Exception:
        return findings

    for db in response.get('DBInstances', []):
        db_id = db['DBInstanceIdentifier']
        db_class = db['DBInstanceClass']

        try:
            metrics = cw.get_metric_statistics(
                Namespace='AWS/RDS',
                MetricName='DatabaseConnections',
                Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_id}],
                StartTime=datetime.now(timezone.utc) - timedelta(days=7),
                EndTime=datetime.now(timezone.utc),
                Period=86400,
                Statistics=['Average']
            )

            datapoints = metrics.get('Datapoints', [])
            if datapoints:
                avg_connections = sum(p.get('Average', 0) for p in datapoints) / len(datapoints)
            else:
                avg_connections = 0

            if avg_connections < 5.0:
                tags = {t['Key']: t['Value'] for t in db.get('TagList', [])}
                cost = get_rds_cost(db_class)
                findings.append({
                    'resource_id': db_id,
                    'resource_type': 'RDS',
                    'region': region,
                    'reason': f'Avg {avg_connections:.1f} DB connections/day over 7 days (threshold: 5.0)',
                    'monthly_cost_usd': cost,
                    'monthly_cost_inr': convert_usd_to_inr(cost),
                    'tags': tags,
                    'detected_at': datetime.now(timezone.utc).isoformat()
                })
        except Exception:
            continue

    return findings


def scan_old_snapshots(session, region):
    ec2 = session.client('ec2', region_name=region)
    findings = []

    try:
        response = ec2.describe_snapshots(OwnerIds=['self'])
    except Exception:
        return findings

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)

    for snapshot in response.get('Snapshots', []):
        snap_start_time = snapshot['StartTime'].replace(tzinfo=timezone.utc)

        if snap_start_time < cutoff_date:
            snap_size_gb = snapshot['VolumeSize']
            tags = {t['Key']: t['Value'] for t in snapshot.get('Tags', [])}
            findings.append({
                'resource_id': snapshot['SnapshotId'],
                'resource_type': 'EBS_SNAPSHOT',
                'region': region,
                'reason': f'{snap_size_gb}GB snapshot from {snap_start_time.date()} (older than 30 days)',
                'monthly_cost_usd': get_snapshot_cost(snap_size_gb),
                'monthly_cost_inr': convert_usd_to_inr(get_snapshot_cost(snap_size_gb)),
                'tags': tags,
                'detected_at': datetime.now(timezone.utc).isoformat()
            })

    return findings


def scan_unused_eips(session, region):
    return scan_unused_eip(session, region)


def scan_idle_rds(session, region):
    return scan_underused_rds(session, region)
