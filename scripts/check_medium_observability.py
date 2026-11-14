"""Verify a medium dashboard and real CloudWatch -> SNS -> SQS alarm/recovery delivery.

Only the isolated NotificationProbe metric is written. Health/scaling alarm states
are never changed. The report excludes message bodies and SQS receipt handles.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import time

from src.moodle_cloud import aws, load_config, outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    config = load_config(args.config)
    if config['size'] != 'medium':
        parser.error('medium configuration required')
    if aws(config, 'sts', 'get-caller-identity')['Account'] != config['account_id']:
        raise RuntimeError('Wrong AWS account')
    out = {k: v['value'] for k, v in outputs(config).items()}
    site = f"{config['project']}-{config['environment']}-med"
    alarm_name = site + '-notification-probe'
    dashboard = aws(config, 'cloudwatch', 'get-dashboard', '--dashboard-name', out['dashboard_name'])
    alarms = aws(config, 'cloudwatch', 'describe-alarms', '--alarm-name-prefix', site + '-')['MetricAlarms']
    operational = [a for a in alarms if a['AlarmName'] != alarm_name]
    report = {
        'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'site': site, 'dashboard_name': out['dashboard_name'],
        'dashboard_widgets': len(json.loads(dashboard['DashboardBody'])['widgets']),
        'alarms': [{'name': a['AlarmName'], 'state': a['StateValue'],
                    'alarm_delivery': out['alarm_topic_arn'] in a.get('AlarmActions', []),
                    'recovery_delivery': out['alarm_topic_arn'] in a.get('OKActions', [])}
                   for a in operational],
        'probe_transitions': [], 'received_notifications': [], 'status': 'running',
    }

    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    def emit(value):
        aws(config, 'cloudwatch', 'put-metric-data', '--namespace', 'MoodleMedium',
            '--metric-data', json.dumps([{'MetricName': 'NotificationProbe', 'Value': value,
                                         'Unit': 'Count', 'Dimensions': [{'Name': 'Site', 'Value': site}]}]))

    def receive():
        result = aws(config, 'sqs', 'receive-message', '--queue-url', out['alarm_queue_url'],
                     '--max-number-of-messages', '10', '--wait-time-seconds', '1', '--visibility-timeout', '15')
        for message in result.get('Messages', []):
            body = json.loads(message['Body'])
            if body.get('AlarmName') != alarm_name or body.get('StateChangeTime', '') < report['started_utc']:
                continue
            state = body.get('NewStateValue')
            if state == 'ALARM' or (state == 'OK' and 'ALARM' in report['probe_transitions']):
                row = {'state': state, 'changed_utc': body['StateChangeTime'], 'message_id': message['MessageId']}
                if row not in report['received_notifications']:
                    report['received_notifications'].append(row)
            aws(config, 'sqs', 'delete-message', '--queue-url', out['alarm_queue_url'],
                '--receipt-handle', message['ReceiptHandle'])

    save()
    try:
        for value, wanted in [(1, 'ALARM'), (0, 'OK')]:
            deadline = time.monotonic() + 360
            while time.monotonic() < deadline:
                emit(value)
                alarm = aws(config, 'cloudwatch', 'describe-alarms', '--alarm-names', alarm_name)['MetricAlarms'][0]
                if alarm['StateValue'] == wanted and wanted not in report['probe_transitions']:
                    report['probe_transitions'].append(wanted)
                    print('Probe evaluation:', wanted, flush=True)
                receive()
                save()
                if wanted in report['probe_transitions'] and any(n['state'] == wanted for n in report['received_notifications']):
                    break
                time.sleep(15)
            else:
                raise RuntimeError(f'Timed out waiting for evaluated {wanted} and its notification')
        report['status'] = 'passed' if (report['dashboard_widgets'] == 11 and len(operational) >= 14
                                       and all(a['alarm_delivery'] and a['recovery_delivery'] for a in report['alarms'])) else 'failed'
    finally:
        # Restore a non-breaching metric even if delivery or an API call fails.
        emit(0)
        report['finished_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
        if report['status'] == 'running':
            report['status'] = 'failed'
        save()
    print('Monitoring check:', report['status'], flush=True)
    return report['status'] != 'passed'


if __name__ == '__main__':
    raise SystemExit(main())
