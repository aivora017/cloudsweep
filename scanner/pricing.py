import os
import csv
from functools import lru_cache

import boto3
import httpx

HOURS_PER_MONTH = 730
DEFAULT_USD_TO_INR = float(os.getenv('USD_TO_INR', '91.94'))

PRICING_DIR = os.path.join(os.path.dirname(__file__), '..', 'ec2_pricing')

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

EBS_SNAPSHOT_PRICING = 0.05  # per GB-month
EIP_HOURLY_COST = 0.005
EIP_MONTHLY_COST = EIP_HOURLY_COST * HOURS_PER_MONTH


@lru_cache(maxsize=1)
def get_usd_to_inr_rate():
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(
                "https://api.exchangerate.host/latest",
                params={"base": "USD", "symbols": "INR"}
            )
            resp.raise_for_status()
            rate = resp.json().get('rates', {}).get('INR')
            if isinstance(rate, (int, float)) and rate > 0:
                return float(rate)
    except Exception:
        pass
    return DEFAULT_USD_TO_INR


def convert_usd_to_inr(usd_amount, rate=None):
    fx_rate = rate if rate is not None else get_usd_to_inr_rate()
    return usd_amount * fx_rate


def load_ec2_pricing_from_csv():
    ec2_pricing = {}

    if not os.path.exists(PRICING_DIR):
        return ec2_pricing

    for csv_file in os.listdir(PRICING_DIR):
        if not csv_file.endswith('.csv'):
            continue
        try:
            with open(os.path.join(PRICING_DIR, csv_file), 'r') as f:
                for row in csv.DictReader(f):
                    instance_type = row.get('Instance type', '').strip()
                    if not instance_type or instance_type in ec2_pricing:
                        continue
                    price_str = row.get('On-Demand Linux pricing', '').strip()
                    if price_str and 'USD' in price_str:
                        try:
                            ec2_pricing[instance_type] = float(price_str.split()[0]) * HOURS_PER_MONTH
                        except (ValueError, IndexError):
                            pass
        except Exception:
            continue

    return ec2_pricing


EC2_PRICING = load_ec2_pricing_from_csv()


def get_ec2_cost(instance_type, default=30.0):
    try:
        pricing = boto3.client('pricing', region_name='us-east-1')
        response = pricing.get_products(
            ServiceCode='AmazonEC2',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'instanceType',    'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': 'Linux'},
                {'Type': 'TERM_MATCH', 'Field': 'tenancy',         'Value': 'Shared'},
                {'Type': 'TERM_MATCH', 'Field': 'capacitystatus',  'Value': 'Used'},
                {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw',  'Value': 'NA'},
            ],
            MaxResults=1,
        )
        if response.get('PriceList'):
            terms = response['PriceList'][0].get('terms', {}).get('OnDemand', {})
            for _, term in terms.items():
                for _, dim in term.get('priceDimensions', {}).items():
                    price = float(dim.get('pricePerUnit', {}).get('USD', '0'))
                    if price > 0:
                        return price * HOURS_PER_MONTH
    except Exception:
        pass
    return EC2_PRICING.get(instance_type, default)


def get_ebs_cost(volume_size, volume_type='gp3'):
    rate = EBS_PRICING.get(volume_type, EBS_PRICING['gp3'])
    return volume_size * rate


def get_rds_cost(instance_class, default=100.0):
    return RDS_PRICING.get(instance_class, default)


def get_snapshot_cost(volume_size):
    return volume_size * EBS_SNAPSHOT_PRICING
