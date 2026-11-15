"""Recalculate the published cost model offline using Decimal; no AWS calls."""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import datetime as dt
import json

HERE = Path(__file__).resolve().parent
D = Decimal
def read(name):
    return json.loads((HERE / name).read_text(encoding='utf-8'))
def money(value):
    return format(value.quantize(D('.01'), rounding=ROUND_HALF_UP), 'f')

billing, inventory, prices = read('billing.json'), read('inventory.json'), read('prices.json')
rates, resources = prices['rates'], inventory['resources']
def select(group, usage_type):
    rows = [r for r in rates[group] if r['attributes'].get('usagetype') == usage_type]
    assert len(rows) == 1, (group, usage_type, len(rows))
    return rows[0]

# Independently check published billing totals before calculating a projection.
gross = sum((D(v) for k, v in billing['record_types_usd'].items() if k not in ('Credit', 'Refund')), D(0))
net = sum((D(v) for v in billing['record_types_usd'].values()), D(0))
assert gross == D(billing['gross_before_credit_refund_usd'])
assert abs(gross - D(billing['independent_daily_gross_usd'])) < D('.000001')
assert abs(gross - sum(map(D, billing['services_gross_usd'].values()), D(0))) < D('.000001')
assert net == D(billing['net_usd'])

running = [i for i in resources['ec2'] if i['state'] == 'running']
assert all(i['type'] == 't3.small' for i in running)
assert all(v['type'] == 'gp3' for v in resources['volumes'])
assert len(resources['rds']) == 1 and resources['rds'][0]['class'] == 'db.t4g.micro'
assert all(r['type'] == 'cache.t4g.micro' for r in resources['redis'])
rows = []
def add(name, quantity, group, usage_type, monthly=False):
    rate = select(group, usage_type)
    hourly = D(quantity) * D(rate['usd']) / (D(730) if monthly else D(1))
    rows.append({'name': name, 'quantity': str(quantity), 'unit': rate['unit'],
                 'usd_per_unit': rate['usd'], 'sku': rate['sku'],
                 'hourly_usd': str(hourly), 'daily_usd': str(hourly * D(24))})

add('EC2 running t3.small (7 at capture)', len(running), 'ec2', 'APS2-BoxUsage:t3.small')
add('RDS PostgreSQL db.t4g.micro Single-AZ', 1, 'rds', 'APS2-InstanceUsage:db.t4g.micro')
add('Redis cache.t4g.micro', sum(x['nodes'] for x in resources['redis']), 'redis', 'APS2-NodeUsage:cache.t4g.micro')
add('Application Load Balancer (hours only)', len(resources['alb']), 'alb', 'APS2-LoadBalancerUsage')
add('NAT Gateway (hours only)', len(resources['nat']), 'nat', 'APS2-NatGateway-Hours')
add('Public IPv4: EC2/EIP union + minimum 2 ALB', inventory['ipv4_counts']['model_total'], 'ipv4', 'APS2-PublicIPv4:InUseAddress')
add('EBS gp3 provisioned storage', sum(v['gib'] for v in resources['volumes']), 'ebs', 'APS2-EBS:VolumeUsage.gp3', True)
add('RDS gp3 provisioned storage', resources['rds'][0]['gib'], 'rds_storage', 'APS2-RDS:GP3-Storage', True)
# EFS is small at capture; reserve 1 GiB for an explicit, reproducible storage assumption.
add('EFS Standard, 1 GiB planning allowance', 1, 'efs', 'APS2-TimedStorage-ByteHrs', True)

hourly = sum((D(x['hourly_usd']) for x in rows), D(0))
local_zone = dt.timezone(dt.timedelta(hours=7))
keep_end = dt.datetime(2026, 12, 1, tzinfo=local_zone).astimezone(dt.timezone.utc)
capture = dt.datetime.fromisoformat(inventory['checked_utc'])
cutoff = dt.datetime.fromisoformat(billing['period']['End']).replace(tzinfo=dt.timezone.utc)
since_capture_hours = D(str((keep_end - capture).total_seconds())) / D(3600)
unbilled_hours = D(str((keep_end - cutoff).total_seconds())) / D(3600)
additional = unbilled_hours * hourly
projected = gross + additional
budget = D(billing['budget_usd'])
result = {
    'model': 'Constant captured configuration at current public OnDemand prices; before credits/tax; not an AWS Cost Explorer forecast',
    'price_checked_utc': prices['checked_utc'], 'inventory_checked_utc': inventory['checked_utc'],
    'keep_through_local': '2026-11-30T23:59:59+07:00', 'end_exclusive_utc': keep_end.isoformat(),
    'billing_end_exclusive_utc': cutoff.isoformat(),
    'hours_after_billing_cutoff': str(unbilled_hours), 'hours_after_inventory_capture': str(since_capture_hours),
    'monthly_storage_proration_hours': 730, 'rows': rows,
    'base_hourly_usd': str(hourly), 'base_daily_usd': str(hourly * D(24)),
    'base_daily_display_usd': money(hourly * D(24)),
    'unbilled_period_base_estimate_usd': str(additional),
    'known_billing_gross_usd': str(gross), 'known_billing_gross_display_usd': money(gross),
    'known_billing_net_display_usd': '0.00' if abs(net) < D('.005') else money(net),
    'known_usage_percent_of_budget': money(gross / budget * D(100)),
    'budget_minus_known_usage_usd': str(budget - gross),
    'projected_gross_through_keep_date_usd': str(projected),
    'projected_gross_display_usd': money(projected),
    'projected_over_budget_display_usd': money(max(projected - budget, D(0))),
    'exclusions': ['Credits/discounts/free-tier entitlements/tax/FX',
                   'ALB LCU, NAT processed GB, cross-AZ/internet transfer, CPU surplus credits',
                   'S3/ECR/snapshot storage, requests, Secrets Manager, CloudWatch logs/metrics/alarms',
                   'Other AWS regions/accounts and autoscaling beyond captured 2 app nodes'],
    'assumptions': ['All 7 captured instances keep running until the selected date',
                    'All captured provisioned EBS/RDS storage is retained',
                    'ALB uses at least two public IPv4 addresses; actual can be higher',
                    'Allocated EIPs and EC2 public IPv4 were deduplicated before counting',
                    'Current configuration is extrapolated from the last billing cutoff, including the current unbilled day',
                    'EFS is budgeted at 1 GiB; monthly storage is prorated using 730 hours',
                    'No resource changes or automatic cleanup are performed by this calculation']
}
(HERE / 'projection.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps({k: result[k] for k in ('known_billing_gross_display_usd', 'known_billing_net_display_usd',
      'base_daily_display_usd', 'hours_after_billing_cutoff', 'projected_gross_display_usd', 'projected_over_budget_display_usd')}, indent=2))
