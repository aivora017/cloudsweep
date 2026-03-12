from datetime import datetime, timedelta, timezone

from moto import mock_ec2

from scanner.findings import scan_orphaned_ebs


@mock_ec2
def test_scan_orphaned_ebs_detects_available_volumes(session):
    ec2 = session.client("ec2", region_name="ap-south-1")

    az = "ap-south-1a"
    ec2.create_volume(
        AvailabilityZone=az,
        Size=50,
        VolumeType="gp3",
        TagSpecifications=[{"ResourceType": "volume", "Tags": [{"Key": "Name", "Value": "orphan"}]}],
    )

    findings = scan_orphaned_ebs(session, "ap-south-1")
    assert len(findings) >= 1
    assert findings[0]["resource_type"] == "EBS"
    assert findings[0]["monthly_cost_usd"] > 0
    assert findings[0]["monthly_cost_inr"] > 0
