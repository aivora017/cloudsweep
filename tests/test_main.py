import json
from click.testing import CliRunner

from scanner.main import main


def _sample_finding(resource_type="EC2", cost_usd=10.0, cost_inr=900.0):
    return {
        "resource_id": "res-1",
        "resource_type": resource_type,
        "region": "ap-south-1",
        "reason": "test",
        "monthly_cost_usd": cost_usd,
        "monthly_cost_inr": cost_inr,
        "tags": {},
        "detected_at": "2026-03-12T00:00:00Z",
    }


def test_main_dry_run_writes_findings_json(monkeypatch, tmp_path):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setattr("scanner.main.scan_idle_ec2", lambda *_: [_sample_finding()])
    monkeypatch.setattr("scanner.main.scan_orphaned_ebs", lambda *_: [])
    monkeypatch.setattr("scanner.main.scan_unused_eip", lambda *_: [])
    monkeypatch.setattr("scanner.main.scan_underused_rds", lambda *_: [])
    monkeypatch.setattr("scanner.main.scan_old_snapshots", lambda *_: [])

    output = tmp_path / "findings.json"
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--dry-run", "--regions", "ap-south-1", "--output", str(output)],
    )

    assert result.exit_code == 0
    assert "Dry-run mode enabled" in result.output

    data = json.loads(output.read_text())
    assert data["summary"]["total_findings"] == 1
    assert data["summary"]["total_waste_inr"] == 900.0


def test_main_non_dry_run_calls_db_and_slack(monkeypatch):
    class _FakeDB:
        def __init__(self, *_):
            pass

        def insert_findings(self, *_):
            return 7

    class _FakeSlack:
        def __init__(self, *_):
            pass

        def send_digest(self, *_):
            return None

        def send_threshold_alert(self, *_):
            return None

    monkeypatch.setenv("DATABASE_URL", "postgresql://fake")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setattr("scanner.main.HAS_DB", True)
    monkeypatch.setattr("scanner.main.HAS_SLACK", True)
    monkeypatch.setattr("scanner.main.ScannerDB", _FakeDB)
    monkeypatch.setattr("scanner.main.SlackNotifier", _FakeSlack)

    monkeypatch.setattr("scanner.main.scan_idle_ec2", lambda *_: [_sample_finding("EC2", 5.0, 450.0)])
    monkeypatch.setattr("scanner.main.scan_orphaned_ebs", lambda *_: [_sample_finding("EBS", 5.0, 450.0)])
    monkeypatch.setattr("scanner.main.scan_unused_eip", lambda *_: [])
    monkeypatch.setattr("scanner.main.scan_underused_rds", lambda *_: [])
    monkeypatch.setattr("scanner.main.scan_old_snapshots", lambda *_: [])

    runner = CliRunner()
    result = runner.invoke(main, ["--regions", "ap-south-1", "--slack"])
    assert result.exit_code == 0
    assert "Stored in database" in result.output
    assert "Slack notification sent" in result.output


def test_main_uses_mock_findings_env(monkeypatch, tmp_path):
    payload = {
        "findings": [_sample_finding("EBS", 4.0, 360.0)],
        "summary": {"total_findings": 1},
    }
    mock_file = tmp_path / "mock.json"
    mock_file.write_text(json.dumps(payload))

    monkeypatch.setenv("USE_MOCK_FINDINGS", "true")
    monkeypatch.setenv("MOCK_FINDINGS_PATH", str(mock_file))

    runner = CliRunner()
    result = runner.invoke(main, ["--dry-run", "--regions", "ap-south-1"])

    assert result.exit_code == 0
    assert "Using mock findings" in result.output


def test_main_handles_scan_exceptions(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setattr("scanner.main.scan_idle_ec2", lambda *_: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr("scanner.main.scan_orphaned_ebs", lambda *_: [])
    monkeypatch.setattr("scanner.main.scan_unused_eip", lambda *_: [])
    monkeypatch.setattr("scanner.main.scan_underused_rds", lambda *_: [])
    monkeypatch.setattr("scanner.main.scan_old_snapshots", lambda *_: [])

    runner = CliRunner()
    result = runner.invoke(main, ["--dry-run", "--regions", "ap-south-1"])

    assert result.exit_code == 0
    assert "Error: boom" in result.output


def test_main_handles_db_and_slack_failures(monkeypatch):
    class _BrokenDB:
        def __init__(self, *_):
            raise RuntimeError("db down")

    class _BrokenSlack:
        def __init__(self, *_):
            pass

        def send_digest(self, *_):
            raise RuntimeError("slack down")

    monkeypatch.setenv("DATABASE_URL", "postgresql://fake")
    monkeypatch.setattr("scanner.main.HAS_DB", True)
    monkeypatch.setattr("scanner.main.HAS_SLACK", True)
    monkeypatch.setattr("scanner.main.ScannerDB", _BrokenDB)
    monkeypatch.setattr("scanner.main.SlackNotifier", _BrokenSlack)

    monkeypatch.setattr("scanner.main.scan_idle_ec2", lambda *_: [_sample_finding()])
    monkeypatch.setattr("scanner.main.scan_orphaned_ebs", lambda *_: [])
    monkeypatch.setattr("scanner.main.scan_unused_eip", lambda *_: [])
    monkeypatch.setattr("scanner.main.scan_underused_rds", lambda *_: [])
    monkeypatch.setattr("scanner.main.scan_old_snapshots", lambda *_: [])

    runner = CliRunner()
    result = runner.invoke(main, ["--regions", "ap-south-1", "--slack"])

    assert result.exit_code == 0
    assert "Database storage failed" in result.output
    assert "Slack notification failed" in result.output
