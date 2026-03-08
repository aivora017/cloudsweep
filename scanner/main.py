import click
import json
import boto3
import os
from datetime import datetime
from scanner.findings import (
    scan_idle_ec2,
    scan_orphaned_ebs,
    scan_unused_eips,
    scan_idle_rds,
    scan_old_snapshots
)

try:
    from db.manager import DatabaseManager
    HAS_DB = True
except ImportError:
    HAS_DB = False

try:
    from notifier.slack import SlackNotifier
    HAS_SLACK = True
except ImportError:
    HAS_SLACK = False


@click.command()
@click.option('--regions',
              default='ap-south-1,us-east-1',
              help='AWS regions to scan')
@click.option('--output', help='Output file for findings')
@click.option('--no-db', is_flag=True, help='Skip database storage')
@click.option('--slack', is_flag=True, help='Send Slack notification')
def main(regions, output, no_db, slack):
    session = boto3.Session()
    region_list = [r.strip() for r in regions.split(',')]

    all_findings = []

    click.echo('CloudSweep Scanner')
    click.echo(f'Scanning regions: {", ".join(region_list)}')
    click.echo('')

    for region in region_list:
        try:
            click.echo(f'Scanning {region}...')

            findings = []
            findings.extend(scan_idle_ec2(session, region))
            findings.extend(scan_orphaned_ebs(session, region))
            findings.extend(scan_unused_eips(session, region))
            findings.extend(scan_idle_rds(session, region))
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
    if output:
        with open(output, 'w') as f:
            json.dump(result, f, indent=2)
        click.echo(f'\nFindings saved to {output}')
    else:
        click.echo(json.dumps(result, indent=2))

    if not no_db and HAS_DB:
        try:
            db_url = os.getenv('DATABASE_URL')
            if db_url:
                db = DatabaseManager(db_url)
                scan_run_id = db.insert_scan_run(region_list, all_findings)
                db.insert_findings(scan_run_id, all_findings)
                click.echo(f'Stored in database (scan_run_id: {scan_run_id})')
        except Exception as e:
            click.echo(f'Database storage failed: {str(e)}', err=True)

    if slack and HAS_SLACK:
        try:
            notifier = SlackNotifier()
            notifier.send_digest(all_findings, result['summary'])
            click.echo('Slack notification sent')
        except Exception as e:
            click.echo(f'Slack notification failed: {str(e)}', err=True)


if __name__ == '__main__':
    main()
