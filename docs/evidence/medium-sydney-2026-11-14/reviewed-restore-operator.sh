#!/bin/bash
set -eu
cloud-init status --wait
systemctl stop moodle-cron.timer moodle-backup.timer
deadline=$((SECONDS+900))
while :; do
  state=$(systemctl show moodle-cron.service --property=ActiveState --value)
  case "$state" in inactive|failed) break ;; esac
  test "$SECONDS" -lt "$deadline"
  sleep 2
done
python3 - <<'PY'
import datetime as dt,json,sys
from pathlib import Path
from psycopg2 import sql
sys.path.insert(0,'/opt/moodle-medium')
from operations import Operations
report={'started_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'scope':'Restore into preprovisioned fresh RDS/EFS; provisioning and credential interruption excluded from load duration'}
class ReviewedRestore(Operations):
    def php(self,*args,migration=False):
        if args[0].endswith('/replace/cli/replace.php'):
            old=next(a.removeprefix('--search=') for a in args if a.startswith('--search='))
            new=next(a.removeprefix('--replace=') for a in args if a.startswith('--replace='))
            if len(new)>len(old):
                connection=self.connect(self.migration)
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT table_name,column_name,character_maximum_length FROM information_schema.columns WHERE table_schema='public' AND left(table_name,4)='mdl_' AND character_maximum_length IS NOT NULL AND data_type IN ('character varying','character')")
                        columns=cursor.fetchall()
                        for table,column,limit in columns:
                            cursor.execute(sql.SQL('SELECT count(*) FROM {} WHERE length(replace({},%s,%s)) > %s').format(sql.Identifier('public',table),sql.Identifier(column)),(old,new,limit))
                            if cursor.fetchone()[0]: raise RuntimeError('URL replacement would truncate a bounded column')
                    report['url_width_preflight']={'columns_checked':len(columns),'overflow_rows':0,'source_length':len(old),'target_length':len(new)}
                    args=(*args,'--shorten')
                finally:
                    connection.close()
        return super().php(*args,migration=migration)
op=None
try:
    op=ReviewedRestore('restore')
    op.restore('s3://moodle-medium-dev-828676179987-ap-southeast-2-backups/moodle-medium-dev-med/20261114T115610')
    report['loaded_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
    report['status']='loaded-maintenance-retained'
    Path('/var/lib/moodledata/.distribution/restore-review.json').write_text(json.dumps(report,indent=2)+'\n')
    print('RESTORE_REVIEW')
    print(json.dumps(report,indent=2))
except Exception as exc:
    print('RESTORE_FAILED '+type(exc).__name__,file=sys.stderr)
    raise SystemExit(1)
finally:
    if op: op.connection.close()
PY
