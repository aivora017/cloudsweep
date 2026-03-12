from datetime import datetime, timedelta, timezone

from moto import mock_cloudwatch, mock_ec2, mock_rds

from scanner.findings import scan_underused_rds, scan_unused_eip, scan_unused_eips


@mock_ec2
def test_scan_unused_eip_detects_unassociated_ip(session):
    ec2 = session.client("ec2", region_name="ap-south-1")
    ec2.allocate_address(Domain="vpc")

    findings = scan_unused_eip(session, "ap-south-1")
    assert len(findings) == 1
    assert findings[0]["resource_type"] == "EIP"
    assert findings[0]["monthly_cost_inr"] > 0


@mock_ec2
def test_scan_unused_eips_alias(session):
    ec2 = session.client("ec2", region_name="ap-south-1")
    ec2.allocate_address(Domain="vpc")

    findings = scan_unused_eips(session, "ap-south-1")
    assert len(findings) == 1


@mock_rds
@mock_cloudwatch
def test_scan_underused_rds_detects_low_connections(session):
    rds = session.client("rds", region_name="ap-south-1")
    cw = session.client("cloudwatch", region_name="ap-south-1")

    rds.create_db_instance(
        DBName="testdb",
        DBInstanceIdentifier="idle-db",
        AllocatedStorage=20,
        DBInstanceClass="db.t3.micro",
        Engine="postgres",
        MasterUsername="admin",
        MasterUserPassword="password123",
    )

    for i in range(1, 8):
        cw.put_metric_data(
            Namespace="AWS/RDS",
            MetricData=[
                {
                    "MetricName": "DatabaseConnections",
                    "Dimensions": [{"Name": "DBInstanceIdentifier", "Value": "idle-db"}],
                    "Timestamp": datetime.now(timezone.utc) - timedelta(days=i),
                    "Value": 1.0,
                    "Unit": "Count",
                }
            ],
        )

    findings = scan_underused_rds(session, "ap-south-1")
    assert len(findings) == 1
    assert findings[0]["resource_type"] == "RDS"
    assert "threshold: 5.0" in findings[0]["reason"]
