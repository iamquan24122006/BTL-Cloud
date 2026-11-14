"""Add an isolated CloudFront HTTPS frontend to an existing small lab without replacing EC2."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import shlex
import subprocess
import sys

from src import moodle_cloud as cli

def source_hash(config):
    digest=hashlib.sha256(json.dumps(config,sort_keys=True).encode())
    for path in sorted((cli.ROOT/'infra/small_public').glob('*.tf'))+[Path(__file__),cli.ROOT/'scripts/small-public-host.py',cli.ROOT/'scripts/small-public-rollback.py',cli.ROOT/'src/moodle_cloud.py']:
        digest.update(path.read_bytes())
    lock=cli.ROOT/'infra/small_public/.terraform.lock.hcl'
    if lock.exists(): digest.update(lock.read_bytes())
    return digest.hexdigest()

def context(config, account):
    if config['size']!='small': raise cli.ConfigError('This frontend supports small only')
    identity=cli.aws(config,'sts','get-caller-identity')
    if identity['Account']!=account: raise cli.ConfigError('AWS account does not match --expected-account')
    instance=cli.instance_id(config)
    target=cli.aws(config,'ec2','describe-instances','--instance-ids',instance)['Reservations'][0]['Instances'][0]
    if target['State']['Name']!='running' or not target.get('PublicDnsName'):
        raise cli.ConfigError('Expected a running EC2 with a public DNS hostname')
    name=f"{config['project']}-{config['environment']}"
    if not any(x['Key']=='Name' and x['Value']==name for x in target.get('Tags',[])):
        raise cli.ConfigError('Instance tag does not match selected lab')
    work=cli.workspace(config)/'public'
    work.mkdir(parents=True,exist_ok=True)
    return name,work,instance,target

def tf(config,work,*args,capture=False):
    env=os.environ.copy()
    env['TF_DATA_DIR']=str(work/'terraform-data')
    env['TF_PLUGIN_CACHE_DIR']=str(cli.ROOT/'.work/provider-cache')
    return cli.run(['terraform','-chdir='+str(cli.ROOT/'infra/small_public'),*args],env=env,capture=capture)

def plan(config,account):
    name,work,instance,target=context(config,account)
    (work/'manifest.json').unlink(missing_ok=True)
    profile=target['IamInstanceProfile']['Arn'].split('/')[-1]
    roles=cli.aws(config,'iam','get-instance-profile','--instance-profile-name',profile)['InstanceProfile']['Roles']
    if len(roles)!=1: raise cli.ConfigError('Expected one instance role')
    tokenfile=work/'origin-token.json'
    if not tokenfile.exists(): tokenfile.write_text(json.dumps({'token':secrets.token_hex(32)}))
    token=json.loads(tokenfile.read_text())['token']
    variables={'account_id':account,'region':config['region'],'name':name,'vpc_id':target['VpcId'],
        'network_interface_id':target['NetworkInterfaces'][0]['NetworkInterfaceId'],
        'origin_dns':target['PublicDnsName'],'instance_role':roles[0]['RoleName'],'origin_token':token}
    varfile=work/'config.tfvars.json'
    varfile.write_text(json.dumps(variables,indent=2))
    tf(config,work,'init','-input=false','-reconfigure','-backend-config=path='+str(work/'terraform.tfstate'))
    tf(config,work,'plan','-input=false','-lock-timeout=60s','-var-file='+str(varfile),'-out='+str(work/'apply.tfplan'))
    details=json.loads(tf(config,work,'show','-json',work/'apply.tfplan',capture=True))
    changes=[(x['address'],x['change']['actions']) for x in details.get('resource_changes',[]) if x['mode']=='managed']
    if any('delete' in actions for _,actions in changes):
        raise cli.ConfigError('Public plan deletes/replaces resources; review manually, apply refused')
    manifest={'account':account,'instance':instance,'fingerprint':source_hash(config),
       'plan_sha256':hashlib.sha256((work/'apply.tfplan').read_bytes()).hexdigest(),
       'changes':changes}
    (work/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print('Public saved plan: '+str(len(changes))+' managed entries; existing EC2/data are not managed by this root.')

def apply(config,account,confirm):
    name,work,instance,_=context(config,account)
    if confirm!=name: raise cli.ConfigError('Exact project-environment confirmation required')
    manifest=json.loads((work/'manifest.json').read_text())
    payload=(work/'apply.tfplan').read_bytes()
    if (manifest['account']!=account or manifest['instance']!=instance or
        manifest['fingerprint']!=source_hash(config) or manifest['plan_sha256']!=hashlib.sha256(payload).hexdigest()):
        raise cli.ConfigError('Plan/source/account/instance changed; re-plan')
    (work/'manifest.json').rename(work/('consumed-'+secrets.token_hex(8)+'.json'))
    private_plan=work/('consumed-'+secrets.token_hex(8)+'.tfplan')
    private_plan.write_bytes(payload)
    tf(config,work,'apply','-input=false','-lock-timeout=60s',private_plan)
    activate(config,account)

def activate(config,account):
    name,work,instance,_=context(config,account)
    output=json.loads(tf(config,work,'output','-json',capture=True))
    url=output['url']['value']
    # Fresh backup before changing canonical URL. No database/schema migration.
    cli.backup(config,wait=True)
    source=base64.b64encode((cli.ROOT/'scripts/small-public-host.py').read_bytes()).decode()
    script="set -eu\numask 077\nexec 9>/run/moodle-backup.lock\nflock -n 9\n"
    script+="printf '%s' "+shlex.quote(source)+" | base64 -d >/opt/moodle-distribution/small-public-host.py\n"
    script+='python3 /opt/moodle-distribution/small-public-host.py '+ ' '.join(map(shlex.quote,[url,config['region'],output['origin_secret_arn']['value']]))
    cli.remote(config,script,wait=True,timeout=1500)
    groups=cli.aws(config,'ec2','describe-security-groups','--filters',
        'Name=tag:Project,Values='+name,'Name=tag:Purpose,Values=small-public')['SecurityGroups']
    if len(groups)!=1: raise cli.ConfigError('Expected exactly one public origin security group')
    (cli.workspace(config)/'public-runtime.json').write_text(json.dumps({'url':url,
        'distribution_id':output['distribution_id']['value'],'origin_security_group_id':groups[0]['GroupId']},indent=2))
    print('Public Moodle: '+url+' ; verify real HTTPS login/file access before acceptance.')

def disable(config,account,confirm):
    name,_,_,_=context(config,account)
    if confirm!=name: raise cli.ConfigError('Exact confirmation required')
    source=base64.b64encode((cli.ROOT/'scripts/small-public-rollback.py').read_bytes()).decode()
    script="set -eu\numask 077\nexec 9>/run/moodle-backup.lock\nflock -n 9\n"
    script+="printf '%s' "+shlex.quote(source)+" | base64 -d >/opt/moodle-distribution/small-public-rollback.py\n"
    script+='python3 /opt/moodle-distribution/small-public-rollback.py'
    cli.remote(config,script,wait=True,timeout=240)
    (cli.workspace(config)/'public-runtime.json').unlink(missing_ok=True)

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True)
    parser.add_argument('--expected-account',required=True)
    sub=parser.add_subparsers(dest='action',required=True)
    sub.add_parser('plan')
    action=sub.add_parser('apply');action.add_argument('--confirm',required=True)
    action=sub.add_parser('activate');action.add_argument('--confirm',required=True)
    action=sub.add_parser('disable');action.add_argument('--confirm',required=True)
    sub.add_parser('status')
    args=parser.parse_args(argv)
    try:
        config=cli.load_config(args.config)
        if args.action=='plan':plan(config,args.expected_account)
        elif args.action=='apply':apply(config,args.expected_account,args.confirm)
        elif args.action=='disable':disable(config,args.expected_account,args.confirm)
        elif args.action=='activate':
            if args.confirm!=f"{config['project']}-{config['environment']}": raise cli.ConfigError('Invalid confirmation')
            activate(config,args.expected_account)
        else:
            _,work,_,_=context(config,args.expected_account)
            out=json.loads(tf(config,work,'output','-json',capture=True))
            print(json.dumps({k:out[k]['value'] for k in ('url','distribution_id')},indent=2))
        return 0
    except (cli.ConfigError,OSError,ValueError,subprocess.CalledProcessError) as exc:
        print('ERROR: '+str(exc),file=sys.stderr)
        return 1

if __name__=='__main__': raise SystemExit(main())
