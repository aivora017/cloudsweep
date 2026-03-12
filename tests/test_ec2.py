from datetime import datetime, timezone

from moto import mock_cloudwatch, mock_ec2

from scanner.findings import scan_idle_ec2


@mock_ec2
@mock_cloudwatch
def test_scan_idle_ec2_detects_low_cpu(monkeypatch, session):
    monkeypatch.setenv("CPU_IDLE_THRESHOLD", "5")

    ec2 = session.client("ec2", region_name="ap-south-1")
    cw = session.client("cloudwatch", region_name="ap-south-1")

    ec2.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1, InstanceType="t2.micro")
    instance_id = ec2.describe_instances()["Reservations"][0]["Instances"][0]["InstanceId"]

    cw.put_metric_data(
        Namespace="AWS/EC2",
        MetricData=[
            {
                "MetricName": "CPUUtilization",
                "Dimensions": [{"Name": "InstanceId", "Value": instance_id}],
                "Timestamp": datetime.now(timezone.utc),
                "Value": 2.0,
                "Unit": "Percent",
            }
        ],
    )

    findings = scan_idle_ec2(session, "ap-south-1")
    assert len(findings) == 1
    assert findings[0]["resource_type"] == "EC2"
    assert findings[0]["resource_id"] == instance_id
    assert findings[0]["monthly_cost_inr"] > 0
