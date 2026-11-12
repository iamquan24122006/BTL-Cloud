"""Configure CloudWatch logs and site-level host metrics on the prepared AMI."""
import json
from pathlib import Path
import subprocess

d = json.loads(Path('/etc/moodle/deploy.json').read_text())
config = {
    'agent': {'metrics_collection_interval': 60},
    'metrics': {'namespace': 'MoodleMedium', 'append_dimensions': {},
                'metrics_collected': {
                    'mem': {'measurement': ['mem_used_percent'], 'append_dimensions': {'Site': d['name']}},
                    'disk': {'measurement': ['used_percent'], 'resources': ['/'], 'drop_device': True,
                             'append_dimensions': {'Site': d['name']}}},
                'aggregation_dimensions': [['Site']]},
    'logs': {'logs_collected': {'files': {'collect_list': [
        {'file_path': '/var/log/cloud-init-output.log', 'log_group_name': d['log_group'], 'log_stream_name': '{instance_id}/bootstrap'},
        {'file_path': '/var/log/moodle-medium.log', 'log_group_name': d['log_group'], 'log_stream_name': '{instance_id}/operations'},
        {'file_path': '/var/lib/docker/containers/*/*-json.log', 'log_group_name': d['log_group'], 'log_stream_name': '{instance_id}/web'},
    ]}}},
}
path = '/opt/aws/amazon-cloudwatch-agent/etc/moodle.json'
Path(path).write_text(json.dumps(config))
subprocess.run(['/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl', '-a', 'fetch-config', '-m', 'ec2', '-s', '-c', 'file:' + path], check=True)
