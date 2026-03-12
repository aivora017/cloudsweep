"""Pricing helpers with AWS Pricing API + CSV fallback and INR conversion."""
import os
import csv
from typing import Dict
from functools import lru_cache

import boto3
import httpx

HOURS_PER_MONTH = 730  # Average hours per month
DEFAULT_USD_TO_INR = float(os.getenv('USD_TO_INR', '91.94'))

PRICING_DIR = os.path.join(
    os.path.dirname(__file__),
    '..',
    'ec2_pricing'
)

EBS_PRICING = {
    'gp2': 0.10,
    'gp3': 0.08,
    'io1': 0.125,
    'st1': 0.045,
    'sc1': 0.025,
}

RDS_PRICING = {
    'db.t3.micro': 30.0,
    'db.t3.small': 61.0,
    'db.t3.medium': 122.0,
    'db.t4g.micro': 25.0,
    'db.t4g.small': 50.0,
    'db.m5.large': 200.0,
    'db.m6i.large': 220.0,
    'db.r5.large': 300.0,
}

# Snapshot storage pricing per GB-month
EBS_SNAPSHOT_PRICING = 0.05  # $0.05 per GB-month

# EIP pricing (for unassociated IPs)
EIP_HOURLY_COST = 0.005  # $0.005/hour when not associated
EIP_MONTHLY_COST = EIP_HOURLY_COST * HOURS_PER_MONTH


def convert_usd_to_inr(usd_amount: float, rate: float | None = None) -> float:
    fx_rate = rate if rate is not None else get_usd_to_inr_rate()
    return usd_amount * fx_rate


@lru_cache(maxsize=1)
def get_usd_to_inr_rate() -> float:
    """Fetch USD/INR and fallback to configured default."""
    url = "https://api.exchangerate.host/latest"
    params = {"base": "USD", "symbols": "INR"}
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            rate = response.json().get('rates', {}).get('INR')
            if isinstance(rate, (int, float)) and rate > 0:
                return float(rate)
    except Exception:
        pass
    return DEFAULT_USD_TO_INR


def _get_pricing_client():
    """AWS Pricing is only available in us-east-1 endpoint."""
    return boto3.client('pricing', region_name='us-east-1')


def load_ec2_pricing_from_csv() -> Dict[str, float]:
    """Load EC2 instance pricing from CSV files.

    Reads all CSV files in ec2_pricing directory and extracts
    'On-Demand Linux pricing' column. Converts hourly rates to monthly.

    Returns:
        Dictionary with instance type as key and monthly USD cost as value.
        Falls back to empty dict if directory not found.
    """
    ec2_pricing = {}

    if not os.path.exists(PRICING_DIR):
        print(f"Warning: Pricing directory not found at {PRICING_DIR}")
        return ec2_pricing

    # Find and process all CSV files in the directory
    csv_files = [f for f in os.listdir(PRICING_DIR) if f.endswith('.csv')]

    for csv_file in csv_files:
        csv_path = os.path.join(PRICING_DIR, csv_file)
        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    instance_type = row.get('Instance type', '').strip()
                    if not instance_type:
                        continue

                    # Skip if we already have this instance type
                    if instance_type in ec2_pricing:
                        continue

                    # Extract hourly price from "X.XXX USD per Hour" format
                    linux_price_str = row.get(
                        'On-Demand Linux pricing', '').strip()
                    if linux_price_str and 'USD' in linux_price_str:
                        try:
                            # Parse "3.616 USD per Hour" format
                            price_value = float(linux_price_str.split()[0])
                            # Convert hourly to monthly
                            monthly_cost = price_value * HOURS_PER_MONTH
                            ec2_pricing[instance_type] = monthly_cost
                        except (ValueError, IndexError):
                            # If parsing fails, skip this row
                            pass
        except Exception as e:
            print(f"Error reading {csv_file}: {e}")
            continue

    return ec2_pricing


def get_ec2_cost(instance_type: str, default: float = 30.0) -> float:
    """Get monthly cost for an EC2 instance type.

    Args:
        instance_type: EC2 instance type (e.g., 't2.micro', 'm5.large')
        default: Default cost if instance type not found

    Returns:
        Monthly USD cost for the instance type
    """
    try:
        pricing = _get_pricing_client()
        response = pricing.get_products(
            ServiceCode='AmazonEC2',
            Filters=[
                  {
                      'Type': 'TERM_MATCH',
                      'Field': 'instanceType',
                      'Value': instance_type,
                  },
                  {
                      'Type': 'TERM_MATCH',
                      'Field': 'operatingSystem',
                      'Value': 'Linux',
                  },
                  {
                      'Type': 'TERM_MATCH',
                      'Field': 'tenancy',
                      'Value': 'Shared',
                  },
                  {
                      'Type': 'TERM_MATCH',
                      'Field': 'capacitystatus',
                      'Value': 'Used',
                  },
                  {
                      'Type': 'TERM_MATCH',
                      'Field': 'preInstalledSw',
                      'Value': 'NA',
                  },
            ],
            MaxResults=1,
        )
        if response.get('PriceList'):
            offer = response['PriceList'][0]
            terms = offer.get('terms', {}).get('OnDemand', {})
            for _, term in terms.items():
                dimensions = term.get('priceDimensions', {})
                for _, dim in dimensions.items():
                    price = float(dim.get('pricePerUnit', {}).get('USD', '0'))
                    if price > 0:
                        return price * HOURS_PER_MONTH
    except Exception:
        pass
    return EC2_PRICING.get(instance_type, default)


def get_ebs_cost(volume_size: int, volume_type: str = 'gp3') -> float:
    """Calculate EBS volume cost.

    Args:
        volume_size: Size in GB
        volume_type: Storage type (gp2, gp3, io1, st1, sc1)

    Returns:
        Monthly USD cost
    """
    rate = EBS_PRICING.get(volume_type, EBS_PRICING['gp3'])
    return volume_size * rate


def get_rds_cost(instance_class: str, default: float = 100.0) -> float:
    """Get monthly cost for an RDS instance.

    Args:
        instance_class: RDS instance class (e.g., 'db.t3.micro')
        default: Default cost if instance class not found

    Returns:
        Monthly USD cost
    """
    return RDS_PRICING.get(instance_class, default)


def get_snapshot_cost(volume_size: int) -> float:
    """Calculate snapshot storage cost.

    Args:
        volume_size: Snapshot size in GB

    Returns:
        Monthly USD cost
    """
    return volume_size * EBS_SNAPSHOT_PRICING


# Load EC2 pricing from CSV at module import time
EC2_PRICING = load_ec2_pricing_from_csv()
