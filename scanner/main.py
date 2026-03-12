import click
import json
import boto3
import os
from datetime import datetime
from scanner.findings import (
    scan_idle_ec2,
    scan_orphaned_ebs,
    scan_unused_eip,
    scan_underused_rds,
    scan_old_snapshots
)

try:
    from scanner.db import ScannerDB
    HAS_DB = True
except ImportError:
    HAS_DB = False

try:
    from notifier.slack import SlackNotifier
    HAS_SLACK = True
except ImportError:
    HAS_SLACK = False


def _strtobool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _has_aws_credentials() -> bool:
    return bool(
        os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY')
    )


def _resolve_mock_findings_path(configured_path: str) -> str:
    if os.path.exists(configured_path):
        return configured_path

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fallback_path = os.path.join(repo_root, 'findings-mock.json')
    return fallback_path


@click.command()
@click.option('--regions',
              default='ap-south-1,us-east-1',
              help='AWS regions to scan')
@click.option('--output', help='Output file for findings')
@click.option('--no-db', is_flag=True, help='Skip database storage')
@click.option('--slack', is_flag=True, help='Send Slack notification')
@click.option(
    '--dry-run',
    is_flag=True,
    help='Read-only mode: skip DB writes and Slack'
)
def main(regions, output, no_db, slack, dry_run):
    region_list = [r.strip() for r in regions.split(',')]

    use_mock_findings = _strtobool(os.getenv('USE_MOCK_FINDINGS', 'false'))
    configured_mock_findings_path = os.getenv(
        'MOCK_FINDINGS_PATH',
        '/app/findings-mock.json'
    )
    mock_findings_path = _resolve_mock_findings_path(
        configured_mock_findings_path
    )

    if dry_run and not use_mock_findings and not _has_aws_credentials():
        use_mock_findings = True
        click.echo(
            'Dry-run without AWS credentials detected; '
            'using bundled mock findings.'
        )

    all_findings = []

    click.echo('CloudSweep Scanner')
    click.echo(f'Scanning regions: {", ".join(region_list)}')
    click.echo('')

    if use_mock_findings:
        try:
            click.echo(f'Using mock findings from {mock_findings_path}')
            with open(mock_findings_path, 'r') as mock_file:
                mock_payload = json.load(mock_file)
            all_findings = mock_payload.get('findings', [])
        except Exception as e:
            click.echo(f'Mock findings load failed: {str(e)}', err=True)
            all_findings = []
    else:
        session = boto3.Session()
        for region in region_list:
            try:
                click.echo(f'Scanning {region}...')

                findings = []
                findings.extend(scan_idle_ec2(session, region))
                findings.extend(scan_orphaned_ebs(session, region))
                findings.extend(scan_unused_eip(session, region))
                findings.extend(scan_underused_rds(session, region))
                findings.extend(scan_old_snapshots(session, region))

                all_findings.extend(findings)
                click.echo(f'  Found {len(findings)} issues')
            except Exception as e:
                click.echo(f'  Error: {str(e)}', err=True)

    total_waste_usd = sum(f['monthly_cost_usd'] for f in all_findings)
    total_waste_inr = sum(f['monthly_cost_inr'] for f in all_findings)

    result = {
        'findings': all_findings,
        'summary': {
            'total_findings': len(all_findings),
            'total_waste_usd': round(total_waste_usd, 2),
            'total_waste_inr': round(total_waste_inr, 2),
            'regions_scanned': region_list,
            'scanned_at': datetime.now().isoformat()
        }
    }

    # Save to file
    effective_output = output
    if dry_run and not effective_output:
        effective_output = 'findings.json'

    if effective_output:
        with open(effective_output, 'w') as f:
            json.dump(result, f, indent=2)
        click.echo(f'\nFindings saved to {effective_output}')
    else:
        click.echo(json.dumps(result, indent=2))

    if not dry_run and not no_db and HAS_DB:
        try:
            db_url = os.getenv('DATABASE_URL')
            if db_url:
                db = ScannerDB(db_url)
                scan_run_id = db.insert_findings(region_list, all_findings)
                click.echo(f'Stored in database (scan_run_id: {scan_run_id})')
        except Exception as e:
            click.echo(f'Database storage failed: {str(e)}', err=True)

    if not dry_run and slack and HAS_SLACK:
        try:
            notifier = SlackNotifier()
            notifier.send_digest(all_findings, result['summary'])
            notifier.send_threshold_alert(all_findings, result['summary'])
            click.echo('Slack notification sent')
        except Exception as e:
            click.echo(f'Slack notification failed: {str(e)}', err=True)

    if dry_run:
        click.echo(
            'Dry-run mode enabled: no database writes or '
            'Slack notifications were performed.'
        )


if __name__ == '__main__':
    main()
