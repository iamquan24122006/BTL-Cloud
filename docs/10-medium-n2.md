# Bàn giao N2 — medium và công cụ triển khai

**Cập nhật bàn giao:** nhánh N2 hiện là `khoi`. Quyền GitHub đã được xác minh lại có WRITE; ghi chú 404 bên dưới là lịch sử. Người dùng yêu cầu dọn lab để ngừng phí; đọc [cleanup](15-aws-cleanup.md) và [hướng dẫn N3](14-n3-acceptance-guide.md) trước khi deploy hoặc truy cập URL cũ.

Phạm vi đối chiếu: `12-dac-ta-tinh-nang-va-nghiem-thu (1).md`, N2, CLI-01…06 và MED-01…12. Công việc nằm trên nhánh local `n2-medium-lab`; chưa lấy được nhánh remote `mq` hoặc push lên remote trước đó trả 404. Medium đã triển khai và kiểm tra trên AWS ngày 09–10/11/2026, gồm thay app, backup/restore và [MED-02 với ACM/HTTPS tại ALB](13-medium-med02.md). N3 kiểm tra lại hồ sơ trước khi chốt toàn bộ tiêu chí.

Kết quả đã chạy cục bộ: [nhật ký kiểm tra N2](11-medium-validation.md), gồm unit test, Terraform mock và Docker integration hai app.

## 1. Thành phần đã bổ sung

Theo lựa chọn của người dùng trong phiên triển khai, có thêm `frontend: cloudfront` cho lab chưa có domain: `domain`, `certificate_arn`, `hosted_zone_id` để rỗng và `wwwroot: auto`. Terraform cấp URL `https://<distribution>.cloudfront.net`, redirect HTTP ở viewer, tắt cache bằng managed CachingDisabled và chuyển mọi cookie/query/header cần thiết về Moodle. ALB HTTP origin chỉ nhận CloudFront origin-facing prefix list. Đây là ngoại lệ truy cập tạm đã được chọn rõ; **không ghi Đạt MED-02** cho HTTPS tại ALB. Cấu hình `frontend: acm` vẫn là đích nghiệm thu gốc.

Các prerequisite có root riêng: `infra/medium_support` (ba bucket, ECR, secret metadata) và `infra/medium_builder` (EC2 Ubuntu sạch, không ingress, SSM, tạo dependency cho AMI). `python -m scripts.medium_lab prepare/plan/apply --account <account>` quản lý saved plan riêng; apply cần `--confirm <account>`. Script không thay đổi máy small và không tạo secret value trong Terraform. Quy trình có chi phí nên phải kiểm tra saved plan và cửa sổ lab trước apply.

| Yêu cầu | Mã và hành vi |
|---|---|
| CLI-01 | `src/medium_config.py`, `config/medium.example.yaml`: schema nghiêm ngặt, không nhận secret value, validate/render offline, giữ từ chối large/production |
| CLI-02 | `preflight`: tool, STS/account, chứng chỉ ACM đã ISSUED và đúng domain/region, AMI x86_64, hai AZ, S3 versioning/encryption/artifact reference; không chứng nhận quyền mutation |
| CLI-03,06 | Saved plan/manifest dùng một lần, fingerprint cả root/template/runtime/CLI/lockfile/artifact reference, kiểm tra account/hash/config; summary create/update/delete/replace; destroy riêng và xác nhận mất dữ liệu |
| CLI-04 | `infra/backend`, backend S3 `encrypt=true,use_lockfile=true`; key `<account>/<project>/<environment>/medium/terraform.tfstate`; workspace riêng, chặn đổi backend âm thầm |
| CLI-05 | `status` chỉ báo outputs; `backup` gửi runner qua SSM, trả command ID và hướng theo dõi, không coi enqueue là thành công |
| MED-01,02 | Hai AZ; ALB public HTTP redirect HTTPS; app/runner private qua một NAT; data subnet không default route Internet; app chỉ nhận port 8080 từ ALB; DNS Route 53 tùy chọn |
| MED-03 | RDS PG16 private, mã hóa, managed master secret; runtime/migration role riêng; `dboptions['ssl']='verify-full'` + CA/libpq; `tls-proof.php` kiểm tra chính kết nối Moodle |
| MED-04 | EFS mã hóa, mount TLS + IAM qua access point UID/GID 33; không mount thì container không khởi động; chỉ `localcachedir` nằm local |
| MED-05,06 | Hai Redis 7.1 riêng, TLS/AUTH; session handler và MUC application mapping cấu hình riêng; DB 0 trên mỗi Redis, namespace theo site; stickiness tắt |
| MED-07 | AMI được chuẩn bị trước, image ECR theo digest, bundle S3 có SHA-256; kiểm tra nhãn source commit; ASG min/desired 2, max 3; app bootstrap không chạy schema install/upgrade |
| MED-08,09 | Runner riêng, lịch cron chỉ bật ở runner; PostgreSQL advisory lock cho operation, PostgreSQL Lock API của Moodle cho task; release duy nhất cài/upgrade, backup trước thay schema đã có |
| MED-10 | Gate PHP chặn mọi request khi chưa active/maintenance/sai release; readiness kiểm DB/schema + Redis + storage; không trả metadata/secret; ASG dùng EC2 health để tránh thay cả cluster khi phụ thuộc chung lỗi |
| MED-11 | Lựa chọn mặc định là **seed fixture tương đương** với small; N3 dùng fixture ở mục 2 dưới đây. Không gọi seed là migration. Restore medium giữ ID theo dump |
| MED-12 | Runner dừng writer app bằng SSM, chặn login DB runtime, khóa cron, dump DB + archive EFS, hash và manifest cuối cùng trên S3; restore vào môi trường mới, đúng source artifact; giữ maintenance sau restore |

Medium này là lab: RDS Single-AZ, mỗi Redis một node, một runner, một NAT. Không tuyên bố HA toàn hệ thống. ALB/NAT/RDS/Redis/EC2/EFS và public IPv4 tính phí; giới hạn thời gian lab và review dự toán trước apply. Alarm đã tạo trên CloudWatch, chưa gắn SNS/email. Health alarm phải được người vận hành theo dõi.

ALB giữ public `Host`, Moodle đặt `sslproxy=true` và `reverseproxy=false`. `reverseproxy=true` trong Moodle 4.5.15 chỉ phù hợp khi proxy chuyển Host sang tên nội bộ; giữ public Host đồng thời bật cờ này gây `reverseproxyabused`. SG app chỉ nhận ALB, nên đường proxy được giới hạn ở mạng.

## 2. Đầu vào cần chuẩn bị cùng N1/N3

1. AWS account/region và phiên AWS CLI của người deploy; quyền tạo VPC/EC2/ALB/ASG/RDS/EFS/ElastiCache/IAM/CloudWatch, `iam:PassRole`, đọc secret Redis cho Terraform. Người mở SSM cần quyền riêng. EC2 app không đọc master/migration secret; runner có quyền vận hành app qua SSM theo tag site.
2. Domain kiểm soát được; ACM certificate **cùng region ALB**, đã xác thực và bao phủ domain. Nếu DNS ngoài Route 53, để `hosted_zone_id: ""`, tạo CNAME domain tới output `alb_dns_name`. Dùng subdomain, không dùng CNAME tại zone apex.
3. Ba bucket riêng: state, artifact, backup. Bật versioning, mã hóa mặc định, block public access, policy từ chối HTTP, không tự xóa backup khi cleanup hạ tầng. Bản này dùng SSE-S3 và secret AWS-managed KMS key. Nếu dùng customer-managed KMS, phải bổ sung key policy/IAM decrypt/encrypt phù hợp trước deploy.
4. Một ECR repository riêng; giữ image digest cũ khi còn backup tham chiếu. Giữ nguyên bundle theo key release; không ghi đè key đã phát hành. ECR bật immutable tags/scan; không có lifecycle policy xóa release đang dùng.
5. Secrets Manager: runtime JSON `{"username":"moodle_runtime","password":"<ngẫu nhiên ít nhất 24 ký tự>"}`; migration tương tự với username `moodle_migration`; Redis JSON `{"token":"<16–128 ký tự tương thích ElastiCache>"}`. Không đưa giá trị vào YAML, argv, Git hay ảnh chụp. Tạo từ file riêng quyền hạn chế bằng `--secret-string file://...`. Ghim `secrets.redis_version` đúng VersionId. Không tự rotate Redis nếu chưa có luồng đổi đồng bộ ElastiCache + runtime + MUC.
6. AMI Ubuntu 26.04 amd64 đã bake, Docker, EFS mount helper, AWS CLI v2, SSM agent, CloudWatch agent, Python/psycopg2 và PG client16. `prepare-host.sh` nhận **đường dẫn tuyệt đối** hai gói `.deb` đã review (amazon-efs-utils/CloudWatch agent) và SHA-256; cài AWS CLI đã kiểm tra trước đó. Script không cài DB server local. Ghi version package, AMI ID, account/region, loại máy và EBS vào bằng chứng. Bootstrap fail rõ nếu thiếu dependency.
7. N3 chuẩn bị `CLOUD-C01`, `CLOUD-C02`, teacher C01, student A/B C01, C chỉ C02, học liệu text/binary tên tiếng Việt, hai bài nộp, điểm/phản hồi và SHA-256. Tạo bằng Moodle chuẩn, guest access tắt, không cấp admin cho teacher/student. Small/medium seed độc lập phải lưu sự tương đương; ID không bắt buộc trùng giữa hai site seed độc lập.

## 3. Kiểm tra offline và build artifact

```powershell
python -m unittest discover -s tests -v
python -m src.moodle_cloud --config config/medium.example.yaml validate
python -m src.moodle_cloud --config config/medium.example.yaml render
terraform -chdir=infra/medium init -backend=false -input=false
terraform -chdir=infra/medium validate
terraform -chdir=infra/medium test
python -m scripts.medium_bundle
```

Ví dụ YAML là placeholder để validate schema; **không thể dùng deploy nguyên trạng**. Render không gọi AWS và không xuất backend vào tfvars. State small cũ ở `.work/<project>-<environment>/` vẫn giữ nguyên.

Image build một lần từ source đã review/commit sạch. Không tự commit/push trong quy trình này. `scripts.medium_bundle --build` từ chối dirty tree để release commit phản ánh đúng mã. Upstream tag `v4.5.15` đã đối chiếu commit `215f44380bdc3ccf852a3a22e34f8423ff64033a`; Dockerfile xác minh lại tag trước checkout.

```powershell
python -m scripts.medium_bundle --build --moodle-commit 215f44380bdc3ccf852a3a22e34f8423ff64033a --tag <account>.dkr.ecr.<region>.amazonaws.com/moodle:<source-commit>
# Login ECR bằng get-login-password qua stdin; push đúng một image build này.
docker push <account>.dkr.ecr.<region>.amazonaws.com/moodle:<source-commit>
aws s3 cp .work/medium-artifact/medium.tar.gz s3://<artifact-bucket>/releases/<source-commit>/medium.tar.gz --sse AES256
```

Điền `artifact.image` theo **digest trả về sau push**, `artifact.release` theo source commit, `artifact.key`, `artifact.sha256` theo bundle. Bundle và image phải cùng source. Lưu Moodle upstream commit, image digest, bundle SHA và package baseline trong hồ sơ. Image kiểm thử với release toàn số 0 không được publish như release thật.

## 4. Bootstrap backend và deploy

Backend là root riêng, dùng local state ở vị trí bảo vệ và sao lưu độc lập. Không lưu state bootstrap bên trong bucket mà chính nó tạo. Có thể dùng root này lần lượt tạo ba bucket (ba workspace/state bootstrap khác nhau), hoặc bucket do nhóm quản lý sẵn với các chính sách tương đương.

```powershell
terraform -chdir=infra/backend init
terraform -chdir=infra/backend plan -var="region=<region>" -var="account_id=<account>" -var="bucket=<state-bucket>" -out=<private-path>/backend.tfplan
# Review saved plan trước khi apply.
terraform -chdir=infra/backend apply <private-path>/backend.tfplan
```

Người deploy cần `s3:ListBucket` đúng prefix; `s3:GetObject/PutObject` cho state; `s3:GetObject/PutObject/DeleteObject` cho `terraform.tfstate.tflock`. Bucket versioning không thay khóa. Không xóa lock thủ công khi chưa xác minh người giữ đã dừng.

Sao chép YAML mẫu thành `config/medium.dev.yaml`, điền identifiers thật; file này chỉ chứa references, không chứa password.

```powershell
python -m src.moodle_cloud --config config/medium.dev.yaml validate
python -m src.moodle_cloud --config config/medium.dev.yaml preflight
python -m src.moodle_cloud --config config/medium.dev.yaml plan
# Review account, create/update/delete/replace, data resources, recurring costs.
python -m src.moodle_cloud --config config/medium.dev.yaml apply --confirm <project>-dev
python -m src.moodle_cloud --config config/medium.dev.yaml status
```

`db_backup_retention_days` mặc định là **7**, nhận số nguyên **1–35** và không cho tắt automated backup. Nếu AWS trả `FreeTierRestrictionError` vì giới hạn retention của Free Plan, chọn **1** cho lab, lập lại saved plan rồi apply tiếp từ state hiện có; không cần tạo lại các tài nguyên đã thành công hoặc nâng cấp account plan. Backup nhất quán database + moodledata lên S3 vẫn là quy trình riêng, phải kiểm chứng restore. Xem [RDS backup retention](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.BackupRetention.html).

Sau apply, dùng output `ssm_shell_command` vào runner, kiểm tra `cloud-init status --wait`, Docker image digest, EFS mount TLS/IAM và log bootstrap. App chưa ready trước release là trạng thái dự kiến; không sửa health thành static 200. Trên runner, tạo riêng `/etc/moodle/admin.json` bằng editor, owner `root:www-data`, mode `0640`, thư mục mode `0750`; JSON gồm `username`, `password`, `email`. Không truyền password bằng lệnh có lịch sử. Chạy:

```bash
sudo /opt/moodle-medium/operation.sh release
sudo tail -n 80 /var/log/moodle-medium.log
sudo cat /var/lib/moodledata/.distribution/operation.json
sudo /opt/moodle-medium/container.sh /opt/moodle-medium/tls-proof.php
sudo systemctl list-timers moodle-cron.timer moodle-backup.timer
```

Đổi mật khẩu admin sau login. Xóa file mật khẩu khởi tạo khi không còn cần. Không bật cron trên app. Release chỉ thành công sau install/upgrade, cấp quyền DML cho runtime, MUC mapping và TLS proof; sau đó mới publish `active.json` và bỏ gate. `operation.json`/log lưu từng bước. Khi lỗi, giữ maintenance, dịch vụ app có thể vẫn dừng, kiểm tra trước retry. Không mặc định xóa lock hoặc dùng `resume` để bỏ qua migration lỗi.

Nếu runner/client bị gián đoạn, `worker-pending.json` ghi container cần kiểm tra và `migration-pending.json` giữ trạng thái schema chưa chắc chắn. Operation mới bị chặn cho tới khi người vận hành xác minh worker đã dừng và chọn phục hồi/restore phù hợp. Timeout dừng/xóa đúng container worker trong lúc còn giữ khóa; không chỉ kill Docker client rồi chạy lại migration. Chỉ xóa marker sau recovery review có bằng chứng.

## 5. Release, backup, restore và chuyển dữ liệu

Mọi operation dùng PostgreSQL advisory lock theo site; process chết thì PostgreSQL giải phóng session lock. Moodle scheduled/ad hoc task có Lock API riêng; Terraform có S3 lock riêng. Hai runner không được cùng migration. Cron chạy `cron.php` rồi `cron-audit.php`; task failure hoặc ad hoc quá hạn 10 phút không phát metric thành công. Kiểm tra lại kết quả task cụ thể theo LMS-05, không chỉ timer/metric.

Role runtime có quyền đọc/ghi và `TRUNCATE` trên bảng Moodle do migration sở hữu; Moodle dùng `TRUNCATE TABLE` khi `delete_records()` không có điều kiện, chẳng hạn tác vụ tag. Quyền này không chuyển ownership, không cho tạo/sửa/xóa cấu trúc trong schema `public`. Bản sửa được kiểm bằng tác vụ `core\task\tag_cron_task` thật trong integration, đồng thời áp dụng cho bảng hiện có và default privileges của migration. [Quyền TRUNCATE của PostgreSQL](https://www.postgresql.org/docs/16/sql-truncate.html).

Trước thay source/schema, giữ image/bundle cũ và backup tương ứng. Cập nhật YAML artifact, plan/review/apply; runtime mới vẫn gated khi chưa khớp release đang active. Trên runner mới chạy `operation.sh release`; luồng dừng mọi app qua SSM, chặn runtime DB login, backup baseline cũ, migrate bằng migration credential và mở lại app. Release lỗi giữ blocked; plan apply lỗi phải giữ state và lập plan mới. Rollback sau thay schema dùng **DB + file + source artifact** của backup, không chỉ quay image.

Khi chỉ đổi mã chạy trên host (`scripts/medium/*`), không build lại image: giữ `artifact.image` và `artifact.release`, phát hành bundle ở **key mới** với SHA riêng rồi vẫn chạy `operation.sh release`. Bootstrap so label image với `artifact.release`, nên đổi `release` mà không đổi image sẽ làm node mới không lên. Quy trình đầy đủ và bản small nằm trong [phát hành mã host](27-host-bundle-deploy.md).

```powershell
python -m src.moodle_cloud --config config/medium.dev.yaml backup
# Lấy CommandId/InstanceId từ output, theo dõi đến trạng thái cuối:
aws --region <region> ssm get-command-invocation --command-id <command-id> --instance-id <runner-id>
```

Timeout/pending/failed chưa phải backup thành công. SSM trả Success vẫn phải kiểm tra prefix S3, manifest cuối, đủ hai file, checksum và restore drill. Backup timer hằng ngày 02:00 UTC. Backup dừng writer trong cả thời gian dump/archive/upload; đây là downtime có chủ đích của lab. Đảm bảo đĩa runner đủ dung lượng tạm cho toàn dataset. Các CLI/script ngoài runner có thể ghi dữ liệu phải được người vận hành dừng trước đợt backup.

Lệnh `backup` dùng khóa local trên runner, tạm dừng `moodle-cron.timer` nếu timer đang active, rồi đợi cron đang chạy kết thúc (tối đa 15 phút) trước khi lấy khóa PostgreSQL. Lần backup thứ hai bị từ chối trước khi tác động timer. Timer được trả về trạng thái ban đầu sau thành công, timeout hoặc lỗi; không bật timer vốn đã dừng. Không giết cron đang ghi file. Nếu dump/upload hoặc recovery lỗi, maintenance vẫn giữ để operator kiểm tra; cron được bật lại cũng không chạy nghiệp vụ trên site còn blocked. Quy tắc này áp dụng cả lệnh CLI và backup timer khi host bundle chứa bản sửa; image Moodle được ghim riêng, không suy source host từ nhãn image.

Restore sang **medium mới**, DB trống và EFS chưa có site active. Dùng config/project mới (state/key/tài nguyên mới), cùng image/source release với backup; `restore_source_prefix` bằng site nguồn (ví dụ `moodle-lab-dev-med`), cùng bucket backup. IAM đích chỉ có quyền đọc source prefix này, không ghi đè nó. Không chạy `release`/seed trước restore.

```bash
sudo /opt/moodle-medium/operation.sh restore --prefix s3://<backup-bucket>/<source-site>/<timestamp>
# Kiểm tra log, hashes, DB/file/fixture và URL đích dưới maintenance.
# config.php đích luôn lấy từ image/config runtime mới, không khôi phục config.php small.
sudo /opt/moodle-medium/operation.sh resume --confirm <target-project>-<environment>-med
```

Restore kiểm format/DB major/source image/digest/checksum, khôi phục bằng migration role, đổi URL bằng Moodle tool replace khi cần, tạo MUC mapping đích và purge cache; giữ blocked đến bước resume có chủ đích. Source secret ARN trong manifest chỉ là tham chiếu; không chép password. Không kỳ vọng session cũ sống sót trên Redis mới: đăng nhập mới rồi thử cùng cookie trên hai node. Chạy lại LMS-01…06 và MED-04…06; giữ IDs từ dump để đối chiếu. N3 đo RPO/RTO từ thời điểm backup và restore thật.

Lựa chọn MED-11 hiện tại là seed fixture tương đương độc lập. Nếu nhóm chọn migrate trực tiếp small thay vì seed, cần chuyển backup small sang hợp đồng restore medium và kiểm chứng riêng trước gọi là migration; không dùng nguyên `config.php` hoặc thay chuỗi mù trong dump.

## 6. State migration, lock test và cleanup

Không dùng `init -reconfigure` để đổi bucket rồi quên state. CLI lưu `.work/.../backend.json` và từ chối backend đổi trong workspace đã bind. Migration có người chịu trách nhiệm: dừng mọi plan/apply, sao lưu `terraform state pull` với quyền hạn chế, ghi lineage/serial/inventory, chuẩn bị IAM/bucket mới, dùng Terraform `init -migrate-state` với đúng `TF_DATA_DIR` và backend config mới. So sánh state pull, lineage/serial, resource inventory và plan trước/sau; cập nhật binding sau khi hoàn thành. Small không tự migrate sang medium, vì hai topology/state khác nhau.

N3 thử khóa trên **môi trường lab** bằng hai phiên Terraform cùng backend/key: phiên A giữ một mutation có kiểm soát, phiên B `plan -lock-timeout=5s` phải chờ hoặc lỗi khóa; lưu output lọc thông tin. Không dùng apply tài nguyên giả trên môi trường thật để thử quyền. Test local/mock không chứng minh S3 lock đang được IAM cho phép.

RDS có deletion protection và final snapshot, EFS có `prevent_destroy`. Do đó plan destroy ban đầu có thể bị từ chối: đây là chốt bảo vệ dữ liệu. Sau restore drill và quyết định hủy dữ liệu, N2 sửa có review `deletion_protection=false`, chọn final snapshot identifier chưa tồn tại và gỡ đúng lifecycle EFS khi cần. Lập/apply plan thay đổi bảo vệ trước, sau đó lập saved destroy plan mới. Không dùng `-target`, không xóa state. Backend/bucket artifact/backup/secret ngoài root medium vẫn giữ; đối chiếu inventory và chi phí sau cleanup.

## 7. Checklist bằng chứng bàn giao N3

Bảng dưới đây là checklist đầy đủ. Kết quả thực chạy ngày 09/11/2026 và giới hạn của từng bằng chứng nằm trong [nhật ký AWS](12-medium-live-lab.md); N3 kiểm tra lại trước khi chốt nghiệm thu toàn bộ.

| Mã | Ca cần chạy và evidence tối thiểu |
|---|---|
| MED-01,02 | Route/SG/IP thực tế; hai AZ; DNS/ACM/listener; HTTP→HTTPS; login/logout/upload qua domain, không loop/mixed content |
| MED-03 | Role runtime khác master; TLS proof chính Moodle; thử cấu hình CA/hostname sai phải thất bại; install/cron/backup thật |
| MED-04…06 | Ghi file A→đọc B hash trùng; cùng cookie qua A/B, course cập nhật/purge không logout; MUC mapping có thể tái tạo |
| MED-07 | Hai target healthy, artifact digest giống nhau; terminate một app trong cửa sổ thử, ASG tạo lại và LMS/file/session hoạt động |
| MED-08,09 | App không có cron; runner xử lý task; `lock-probe.php` cùng lúc trên runner/app chỉ một bên ACQUIRED; hai release cùng lúc chỉ một bên giữ operation lock |
| MED-10 | EFS thiếu, secret sai, bootstrap chưa xong và blocked đều không ready; thử trực tiếp app qua SSM để chứng minh gate 503 dù ALB fail-open |
| MED-11 | Chọn seed tương đương hoặc migration; ghi rõ lựa chọn, fixture, role/enrolment/assignment/file/grade; không trộn hai khái niệm |
| MED-12 | Backup ID/timestamps/manifest/hashes, restore medium mới, IDs, LMS đầy đủ, session/file A/B sau restore; RPO/RTO đo thật |
| CLI-04…06 | Hai phiên tranh khóa, state lineage/serial/inventory; command ID SSM đến terminal; saved destroy plan/backup trước hủy |

Xác định app xử lý request bằng log stream nội bộ theo instance; access log chỉ ghi method/path/status/duration, không query/cookie/referer. Không mở debug endpoint public. Giới hạn request Apache/PHP/Moodle là 64 MiB; multipart có overhead nên dùng file hợp lệ nhỏ hơn giới hạn (ví dụ 60 MiB), ca >64 MiB phải từ chối rõ. Kiểm tra desktop và màn hình hẹp trên đúng trình duyệt đã ghi, không tuyên bố tương thích chưa thử.

## 8. Nguồn cấu hình đã đối chiếu

- [Native PostgreSQL driver Moodle 4.5.15](https://github.com/moodle/moodle/blob/v4.5.15/lib/dml/pgsql_native_moodle_database.php): tùy chọn `dboptions['ssl']` được truyền vào libpq.
- [Moodle config baseline](https://github.com/moodle/moodle/blob/v4.5.15/config-dist.php): session Redis TLS, proxy, shared cache/temp và localcachedir.
- [Moodle URL/proxy validation](https://github.com/moodle/moodle/blob/v4.5.15/lib/setuplib.php): chọn cờ proxy theo chính sách Host thực tế.
- [MUC config writer](https://github.com/moodle/moodle/blob/v4.5.15/cache/classes/config_writer.php) và [Redis store](https://github.com/moodle/moodle/blob/v4.5.15/cache/stores/redis/lib.php): mapping/API đúng phiên bản, cafile TLS.
- [HashiCorp S3 backend](https://developer.hashicorp.com/terraform/language/backend/s3): `use_lockfile` và quyền `.tflock`.
- [RDS PostgreSQL TLS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.Concepts.General.SSL.html): verify-full/CA/hostname.
