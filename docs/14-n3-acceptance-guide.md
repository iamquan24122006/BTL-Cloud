# Hướng dẫn N3 — kiểm thử, vận hành, đo tải và bàn giao

Đối tượng: N3 theo `12-dac-ta-tinh-nang-va-nghiem-thu (1).md`. Đọc cùng [đặc tả đầy đủ trên nhánh mq](https://github.com/iamquan24122006/BTL-Cloud/blob/2d42889/docs/12-dac-ta-tinh-nang-va-nghiem-thu.md), [bàn giao N2](10-medium-n2.md), [test plan](06-test-plan.md) và [vận hành](05-operations.md). Đặc tả đầy đủ có OPS, OBS, SEC, COST, QA và AT-01…20; bản `.md` người dùng gửi ở máy triển khai kết thúc ở MED-12.

**Trạng thái sau đợt bàn giao:** người dùng yêu cầu dọn AWS để ngừng phí. Xem [biên bản cleanup](15-aws-cleanup.md) để biết tài nguyên thực sự đã xóa và phần còn lại. Các URL/AMI/ARN/instance ID trong hồ sơ 09–10/11/2026 là bằng chứng lịch sử; không dùng chúng như môi trường đang chạy. Không thể chạy ca AWS trước khi dựng lại. Backup/state/credential và image offline nằm ngoài Git, trên máy người triển khai.

## 1. N3 cần giao những gì

1. Ma trận yêu cầu → ca thử → kết quả → đường dẫn bằng chứng, có người thực hiện và người kiểm tra lại.
2. Nghiệm thu LMS trên small, medium và đích sau restore; kiểm tra quyền bằng URL/request thật.
3. Quy trình backup/restore, thử lỗi và recovery có log; RPO/RTO đo từ drill thật.
4. Dữ liệu đo tải small/medium, JMX, raw result giữ riêng, bảng tổng hợp và giới hạn diễn giải.
5. Log/metric/dashboard/cảnh báo có thử kênh nhận; sổ chi phí và inventory trước/sau cleanup.
6. Báo cáo, kịch bản demo và bàn giao để người khác làm theo được.

N1 sửa phần small; N2 sửa medium/runtime/CLI medium. N3 ghi lỗi tái hiện và kiểm tra lại bản sửa. Không đổi `Chờ nghiệm thu` thành `Đạt` chỉ vì unit test hoặc Terraform apply thành công.

## 2. Phân biệt nhánh và tài khoản trước khi chạy

Nhánh `khoi` chứa phần N2 và hướng dẫn này. Nhánh `mq` có tiến độ small của N1 cùng các công cụ small mới hơn. Hai nhánh có thay đổi khác nhau trong `src/moodle_cloud.py`; **không chép đè CLI của nhánh này lên nhánh kia**. N3 dùng hai checkout riêng hoặc phối hợp N1/N2 merge và chạy lại test trước khi dùng một bản tích hợp.

```powershell
git clone --branch khoi https://github.com/iamquan24122006/BTL-Cloud.git BTL-Cloud-N2
Set-Location BTL-Cloud-N2
git fetch origin
git worktree add ../BTL-Cloud-N1 origin/mq
git rev-parse HEAD
git status --short
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Ví dụ dưới dùng `python` trong virtualenv đã kích hoạt hoặc thay bằng `.\.venv\Scripts\python.exe`. Cần Git, Python >=3.11, Terraform >=1.10,<2, AWS CLI v2, Session Manager plugin và Docker cho build. JMeter/Java cần cho đo tải. Chạy `python -m src.moodle_cloud --help` **ở đúng checkout**; các lệnh `health`, `backup --wait`, `restore` của small trên mq không tự có trên bản CLI medium này.

Trước mỗi phiên AWS:

```powershell
$env:AWS_PROFILE = '<profile-cua-lab>'
$Region = 'ap-southeast-1'
aws sts get-caller-identity --region $Region
python -m src.moodle_cloud doctor
```

Đối chiếu account với YAML và người giữ tài khoản. Đợt medium trước dùng account `860366539351`, Singapore. Small mới của N1 trên mq ghi Sydney và profile khác; không suy ra nó thuộc cùng account. Không destroy tài nguyên của N1 ở account khác từ state medium. Không gửi access key/password qua Git hoặc log nghiệm thu.

## 3. Chuẩn bị hồ sơ một lượt chạy

```powershell
$Run = 'n3-20261110-01' # Đổi theo ngày/lượt thực tế.
New-Item -ItemType Directory -Force ".work/n3/$Run", ".work/n3/$Run/private" | Out-Null
Copy-Item docs/templates/n3-results.csv ".work/n3/$Run/results.csv"
Copy-Item docs/templates/n3-run.md ".work/n3/$Run/run.md"
```

Giới hạn ACL thư mục `private` cho người vận hành; `.work` đã bị Git ignore nhưng ignore không phải mã hóa/kiểm soát quyền. State, plan, dump, tar moodledata, thông tin đăng nhập, CSV người dùng JMeter và cookie giữ trong khu vực riêng. Chỉ đưa JSON/bảng tổng hợp, log đã lọc và ảnh đã kiểm tra vào `docs/evidence/<run>/`.

Điền commit, account/region, preset, AMI, image digest, bundle SHA, phiên bản Moodle/PHP/PG, giới hạn upload, CPU credit mode, fixture và thời gian UTC. Mỗi ca phải ghi kết quả kỳ vọng, kết quả thật, exit code và đường dẫn bằng chứng. Với ảnh: ghi browser/version, viewport; viewport hẹp không đồng nghĩa thiết bị di động thật.

## 4. Kiểm tra offline trước khi tốn phí

Ở checkout khoi:

```powershell
python -m unittest discover -s tests -v
python -m src.moodle_cloud --config config/medium.example.yaml validate
python -m src.moodle_cloud --config config/medium.example.yaml render
terraform fmt -check -recursive infra
terraform -chdir=infra/medium init -backend=false -input=false
terraform -chdir=infra/medium validate
terraform -chdir=infra/medium test
python -m scripts.medium_bundle
```

Lưu số test và exit code thực tế. Unit/mock test không tạo AWS và không chứng minh IAM/SSM/EFS/HTTPS thật. Khi thay runtime, chạy thêm `python -m scripts.check_medium_runtime --image <image-vua-build>` theo [nhật ký validation](11-medium-validation.md). Không dùng image CI có release toàn số 0 để deploy.

AT-01/02: dùng bản sao YAML trong `.work/n3/<run>/`, thử khóa lạ/trùng, thiếu trường, sai kiểu, preset large/production, secret value và confirm sai. Xem các trường hợp trong `tests/test_cli.py` và test medium để tránh tự nghĩ cú pháp không thuộc schema. Test account/source/plan đổi cần dùng mock hoặc saved plan của môi trường lab riêng; không sửa state/plan production. Sau apply lỗi phải lập plan mới; không tái dùng manifest đã consumed.

## 5. Dựng lại medium sau cleanup

N3 phối hợp N2 bước này. Không chạy lại `.work/medium-live/medium.yaml` cũ: bucket, AMI, certificate, secret và ECR trong đó có thể đã bị xóa. Dành cửa sổ lab có giờ kết thúc và dự toán; topology trước khoảng 10–12 USD/ngày khi gồm cả small cũ, không phải báo giá cố định cho lần dựng mới.

### 5.1. Bucket, ECR và builder

```powershell
$Account = '<account-12-chu-so>'
$Project = 'moodle-n3'
python -m scripts.medium_lab prepare --account $Account --region $Region --project $Project
python -m scripts.medium_lab plan --account $Account --region $Region --project $Project
# Review cả hai saved plan support và builder; kiểm tra account, tên và phí.
python -m scripts.medium_lab apply --account $Account --region $Region --project $Project --confirm $Account
```

Nếu account Free plan từ chối builder `t3.medium`, chạy lại `prepare` với `--builder-instance-type t3.small`, rồi lập/review plan mới trên **state hiện có** trước khi apply. Mặc định vẫn là `t3.medium`. Lượt N3 ngày 11/11 đã xác minh builder `t3.small` tạo được AMI đủ dependency; không tự nâng cấp billing để vượt giới hạn account. Kiểm tra thêm quota vCPU và loại máy trong YAML medium trước apply; quyền đọc inventory không chứng minh mọi thao tác tạo tài nguyên sẽ được phép.

`prepare` tải dependency từ nguồn chính thức và ghi hash; `plan`/`apply` quản lý hai root riêng. Không đổi project giữa các bước. Kết quả nằm ở `.work/medium-live/medium_support/outputs.json` và `medium_builder/outputs.json`; giữ cả local state bootstrap riêng, không đặt nó trong chính bucket đang quản lý.

Lấy builder ID, vào SSM và kiểm tra:

```bash
sudo cloud-init status --wait
sudo test -f /var/lib/moodle-distribution/medium-ami-ready
sudo docker version
sudo systemctl status amazon-ssm-agent --no-pager
```

N2 kiểm phiên bản dependency và chuẩn bị AMI sạch: xóa file tải tạm của builder, `cloud-init clean --logs --machine-id`, rồi tạo AMI bằng `aws ec2 create-image`; chờ `image-available`. Ghi AMI và snapshot ID. Không chứa secret/site data trong AMI. Sau khi bake xong dọn builder theo saved destroy plan; chỉ stop vẫn giữ phí EBS.

### 5.2. Secret và artifact

Tạo giá trị mới cho bốn secret metadata từ outputs support: `runtime`, `migration`, `redis`, `admin`. Cấu trúc JSON và yêu cầu độ dài ở [mục đầu vào N2](10-medium-n2.md#2-đầu-vào-cần-chuẩn-bị-cùng-n1n3). Chuẩn bị file JSON bằng editor trong thư mục private; không ghi password literal vào command history. Với từng ARN:

```powershell
aws secretsmanager put-secret-value --region $Region --secret-id '<ARN-tu-output>' --secret-string file://.work/n3/<run>/private/<loai>.json --query VersionId --output text
```

Lưu VersionId của Redis vào YAML. Admin JSON gồm `username`, `password`, `email`; giữ riêng bản khởi tạo dùng seed/check. App không đọc migration/master secret. Ghi metadata ARN/version được phép chia sẻ, không ghi giá trị.

Build từ commit sạch; làm đúng luồng [build/publish N2](10-medium-n2.md#3-kiểm-tra-offline-và-build-artifact): `scripts.medium_bundle --build`, ECR login bằng password qua stdin, push image, upload bundle S3, lấy digest và SHA-256. Không dùng `latest`. Có thể dùng image offline đã lưu **đúng release cũ** để restore backup cũ, xem mục 10; không gắn nhãn source commit mới lên image cũ.

### 5.3. Domain, ACM và YAML

Giữ quyền quản lý Dynu; đăng nhập bằng thông tin nhận riêng từ chủ tài khoản. Host đã dùng: `www.moodle-cloud-distribution.mywire.org`. Nếu ACM cũ đã xóa, yêu cầu chứng chỉ public mới cho đúng host ở Singapore, thêm CNAME validation mới tại Dynu và đợi `ISSUED`. Không mặc định CNAME cũ xác thực mọi chứng chỉ mới.

Copy `config/medium.example.yaml` vào `.work/n3/<run>/medium.yaml`, điền identifiers mới: account, project, region, hai AZ, AMI, ba bucket, ECR digest, release commit, bundle key/hash, secret ARNs/Redis version, cert ARN. Dùng `frontend: acm`, `domain` là host ở trên, `wwwroot` là URL HTTPS cùng host, `hosted_zone_id: ''` khi DNS ở Dynu. Dùng CIDR không trùng môi trường khác. YAML mẫu không deploy nguyên trạng được.

```powershell
$Config = ".work/n3/$Run/medium.yaml"
python -m src.moodle_cloud --config $Config validate
python -m src.moodle_cloud --config $Config preflight
python -m src.moodle_cloud --config $Config plan
# Review create/update/delete/replace, dữ liệu và recurring cost.
python -m src.moodle_cloud --config $Config apply --confirm "$Project-dev"
python -m src.moodle_cloud --config $Config status
```

Cập nhật CNAME `www` tới `alb_dns_name` mới, không dùng IP cố định. Đợi DNS công khai đúng. `status` chỉ là Terraform outputs. Kiểm tra cloud-init, mount EFS, image digest và SSM trên runner/cả hai app. App chưa ready trước release là dự kiến.

Trên runner mới, nếu dựng fixture mới (không phải restore):

```bash
sudo /opt/moodle-medium/operation.sh release
sudo /opt/moodle-medium/container.sh /opt/moodle-medium/tls-proof.php
sudo systemctl list-timers moodle-cron.timer moodle-backup.timer
```

Đợi release thực sự hoàn tất, hai target healthy rồi mới nghiệm thu. Nếu restore, **không release/seed trước**, xem mục 10. Sau đổi password admin, cập nhật file credential hiện hành riêng; password fixture được seed từ secret admin khởi tạo, không mặc định đổi theo password admin mới.

## 6. Fixture và kiểm tra LMS qua HTTP/browser

### 6.1. Fixture chuẩn

Ở checkout khoi, sau khi release sạch thành công:

```powershell
python -m scripts.acceptance.aws_seed --config $Config --confirm "$Project-dev" --output ".work/n3/$Run/fixture.json"
```

Script chỉ dành medium runner lab, dừng/drain cron và giữ operation lock; lưu IDs/hashes, không in password. Fixture: course riêng `CLOUD-C01/CLOUD-C02`, `cloud_teacher`, `cloud_student_a/b/c`, role/enrolment, text/binary tiếng Việt, assignment, bài nộp và điểm/phản hồi. Kiểm lại manifest; chạy seed lặp không thay thế ca thao tác GUI. Cùng fixture cho small nhưng ID có thể khác khi seed độc lập.

File admin cấp cho checker phải khớp password admin hiện hành và khóa HMAC đã dùng khi seed. Checker hiện dùng một password cho cả hai mục đích. Nếu admin đã đổi sau seed, không đổi ngược mật khẩu để làm test xanh: N2 điều chỉnh checker tách hai credential hoặc N3 kiểm tra bằng tài khoản fixture thực tế và ghi giới hạn công cụ. Không seed lại lên bản restore để che mất dữ liệu.

### 6.2. Bộ checker có sẵn

```powershell
$Url = 'https://www.moodle-cloud-distribution.mywire.org'
$Admin = ".work/n3/$Run/private/admin.json"
$Fixture = ".work/n3/$Run/fixture.json"
python -m scripts.acceptance.http_check --url $Url --fixture $Fixture --admin-credentials $Admin --output ".work/n3/$Run/http.json"
python -m scripts.acceptance.https_check --url $Url --alb-dns '<DNS-ALB-moi>' --fixture $Fixture --admin-credentials $Admin --output ".work/n3/$Run/https.json"
```

Mốc N2 đã có **47 kiểm tra HTTP và 16 kiểm tra HTTPS đạt** trên domain cũ trong [hồ sơ MED-02](evidence/medium-med02-2026-11-10/README.md). N3 ghi số chạy thực tế của mình. Checker HTTP chỉ chấp nhận HTTPS, không dùng nguyên trạng cho small localhost HTTP. Small dùng công cụ của checkout mq hoặc thao tác tương đương với N1.

**Giới hạn:** lặp request qua ALB chưa chứng minh request tới cả A và B; phải đối chiếu log từng node ở mục 7. Checker cũng không chứng minh GUI upload, responsive thật, mọi lỗi UI, file >64 MiB, task kết quả, scaling hay toàn bộ ca restore.

### 6.3. Walkthrough và upload bổ sung

1. Mở cửa sổ riêng cho admin/teacher/student A/B/C và guest. Ghi browser/version/viewport; desktop và màn hình hẹp. Không dùng chung cookie giữa vai trò.
2. Admin kiểm tên site, enrolment và guest access tắt. Teacher tạo/sửa section/học liệu; student A/B đọc được, C không đọc bằng URL trực tiếp.
3. Teacher upload một `.txt` và file nhị phân tên tiếng Việt có khoảng trắng qua file picker. Student tải lại; so `Get-FileHash -Algorithm SHA256` với nguồn, ghi byte và MIME. Nội dung HTML login có HTTP 200 không phải tải file đạt.
4. Kiểm giới hạn thực tế ở Moodle, PHP và Apache. Baseline medium công bố 64 MiB; multipart có overhead, dùng file hợp lệ khoảng 60 MiB. Tạo file test 65 MiB rồi upload: phải bị từ chối rõ, không tạo resource/submission giả thành công. Ghi nguyên thông báo/HTTP status; 413 hợp lý nhưng trang trắng không đủ chứng minh trải nghiệm đạt.
5. A/B nộp hai file khác nhau; teacher tải và chấm từng bài. Reload/đăng nhập lại kiểm điểm/phản hồi, hash bài; A không lấy file/điểm B, student không sửa điểm/assignment. Ghi chính sách hạn nộp/resubmission, không suy ra được phép sửa sau khóa.
6. Logout rồi gửi request mới tới file riêng; replay cookie cũ không đọc được. Kiểm sai mật khẩu, phiên hết hạn, maintenance và thông báo quá dung lượng.
7. Theo DevTools kiểm URL, ảnh, CSS, form action đều HTTPS, không loop/mixed content; cookie Secure/HttpOnly đúng host. Ảnh chụp không chứa password/cookie/token.

Tạo file lớn không cần tải Internet:

```powershell
$File = [IO.File]::Create((Join-Path (Get-Location) ".work/n3/$Run/upload-65MiB.bin"))
try { $File.SetLength(65 * 1MB) } finally { $File.Dispose() }
Get-FileHash ".work/n3/$Run/upload-65MiB.bin" -Algorithm SHA256
```

## 7. Nghiệm thu nhiều node và khả năng thay app

Lấy ASG name, TG ARN, runner ID và app IDs mới từ `status`/AWS, không copy ID trong ảnh cũ. Tắt stickiness khi chứng minh session. Lưu `describe-target-health`, `describe-instances`, subnet/route/SG, launch template version và image digest, không dump nguyên config có secret.

### 7.1. File, session và MUC — MED-04…06, AT-13/14

1. Login A qua ALB, giữ cùng cookie. Upload học liệu/bài nộp, tải nhiều lần và so SHA-256.
2. Qua SSM trên từng app, đối chiếu log `moodle-medium-web`/CloudWatch stream theo instance trong cùng khoảng UTC. Cần có request file thành công trên **cả hai** node. Chỉ ghi method/path/status/time; không thêm endpoint debug public hoặc log cookie/query.
3. Nếu ALB chưa đưa request qua đủ hai node, thực hiện cửa sổ test: deregister A khỏi TG, đợi draining xong và chứng minh request qua B bằng log; register A lại và đợi healthy, rồi làm ngược lại. Luôn giữ một app healthy; không sửa SG mở public. Đoạn này chỉ dành staging, ghi mọi lỗi trong chuyển tiếp.
4. Cùng cookie phải giữ đúng user và quyền; request qua node B tải file do A xử lý có hash trùng. Xác minh EFS mount TLS/IAM, access point UID/GID 33 và localcachedir riêng.
5. Teacher sửa course qua A, student thấy qua B. Trên runner chạy `sudo /opt/moodle-medium/container.sh /var/www/moodle/admin/cli/purge_caches.php`; phiên A vẫn đăng nhập, nội dung mới nhất và site khác không bị purge ngoài ý muốn.
6. Lưu mapping MUC từ giao diện admin hoặc output đã lọc; có script tái tạo `scripts/medium/muc.php`. Không gọi chỉ cấu hình session Redis là đã có MUC.

### 7.2. ASG — MED-07, AT-15

1. Chốt baseline hai app healthy, cùng release/image, fixture/file và cookie đã lưu riêng. Ghi min/desired/max thực tế.
2. Trên staging, dùng `aws autoscaling terminate-instance-in-auto-scaling-group --instance-id <mot-app> --no-should-decrement-desired-capacity --region <region>`; kiểm đúng app ID, không runner/small.
3. Đánh dấu thời gian, xem ASG activities/EC2/SSM và TG; chờ app mới bootstrap/mount/ready. Ghi thời gian thay và lỗi request thực tế, không tuyên bố zero downtime từ một trang còn mở.
4. Dùng cùng phiên kiểm course, học liệu, bài nộp, điểm và hash; app mới cùng digest, không chạy install/upgrade DB trong user-data.
5. Thử scaling policy riêng sau baseline: quan sát CPU/policy/activities khi tải đủ, scale-out tối đa 3 và scale-in. Thay desired bằng tay chỉ chứng minh điều khiển capacity, không chứng minh policy hoạt động. Sau thử trả baseline 2; lưu khoảng thời gian và phí app thứ ba.

## 8. Cron, khóa và thử lỗi có kiểm soát

### 8.1. Cron/Lock API/operation lock — MED-08/09

Trên runner kiểm timer/journal và trang Scheduled/Ad hoc tasks: một task thực sự xử lý, `lastruntime`/backlog thay đổi. `cron.php` exit 0 chưa đủ nếu task riêng lỗi; `cron-audit.php` và metric CronSuccess phải phản ánh tình trạng. Trên từng app xác minh cron timer không enabled/running ngoài ý muốn.

Hai terminal SSM, một app và runner, chạy gần cùng lúc:

```bash
sudo /opt/moodle-medium/container.sh /opt/moodle-medium/lock-probe.php
```

Probe giữ cùng Moodle Lock API trong 20 giây: một bên `ACQUIRED`/exit 0, bên kia `BUSY`/exit 3. Ghi thời gian chồng lấn; nếu chạy nối tiếp cả hai ACQUIRED không phải lỗi khóa nhưng không đủ ca tranh chấp.

Operation lock khác Lock API: trên **staging đã backup**, hai phiên runner thử release đồng thời theo cửa sổ thống nhất với N2. Chỉ một phiên được vào install/upgrade, phiên còn lại bị từ chối/chờ có giới hạn; đối chiếu log bước và schema. Cần đủ thời gian chồng lấn để có tranh chấp. Không phá PostgreSQL lock hoặc xóa marker để ép thành công. Dùng test runtime local khi chưa có staging; ghi chưa chứng minh trên AWS.

### 8.2. Readiness/TLS/backup lỗi — MED-03/10, OPS-06

Mỗi ca: ghi baseline → tạo một lỗi → request trực tiếp app qua SSM/tunnel và qua ALB → log/metric → khôi phục → kiểm lại LMS. Đánh dấu lại hai target healthy trước ca tiếp theo. Các lỗi thiếu secret/artifact/EFS nên dùng node/cluster staging riêng, không sửa đồng thời mọi app của bản đang demo.

| Ca | Cách thực hiện trong lab riêng | Kỳ vọng và recovery |
|---|---|---|
| Thiếu EFS | N2 dựng app test với mount thất bại, dừng web trước thay mount | Bootstrap/container từ chối; không ghi vào thư mục local thay EFS. Khôi phục mount TLS/IAM rồi bootstrap/web và kiểm hash |
| Secret/Redis sai | Bản config staging riêng tham chiếu secret/token sai; giữ bản đúng riêng | Gate/readiness không báo 200; log được lọc, không lộ token. Khôi phục secret/version đồng bộ rồi kiểm login |
| CA/hostname DB sai | One-off test container cùng PHP/Moodle, mount bản config/CA test riêng; không sửa file đang dùng của cả cluster | `verify-full` từ chối kết nối, không fallback plaintext. N2 xác nhận test thực dùng driver Moodle; khôi phục config, TLS proof lại đạt |
| Artifact thiếu/sai hash | Node staging riêng dùng key/digest/hash test không hợp lệ | Bootstrap dừng rõ, không chạy release ngẫu nhiên; trả reference đúng rồi dựng lại node |
| Maintenance/bootstrap chưa xong | Kiểm gate đang blocked và trước release sạch | Request ứng dụng 503 dù Apache sống. Thử trực tiếp vì ALB có thể fail-open khi mọi target unhealthy |
| Cron runner dừng | Dừng timer trong cửa sổ test; ghi thời điểm task không tiến triển | CronSuccess missing được phát hiện; start timer/service, task chạy tiếp và backlog được kiểm |
| S3 upload bị từ chối | Bucket/prefix đích test riêng thiếu PutObject, không sửa bucket nguồn cuối cùng | Backup trả lỗi, không có manifest hoàn tất; kiểm trạng thái web/cron/maintenance thực tế trước recovery |
| Restore/migration bị gián đoạn | Đích staging riêng, có backup nguồn đã kiểm và artifact tương ứng | Không mở site dở; xem pending markers/worker còn chạy, chọn retry/restore có N2 review, giữ log trước khi xử lý |

Không unmount cưỡng bức EFS đang có writer, không làm đầy disk DB, không công bố fallback plaintext/HA DB/cache. Những ca chưa có công cụ an toàn hoặc chưa chạy để `Chờ nghiệm thu`, ghi điều kiện cần N2 hỗ trợ.

## 9. Backup, lịch chạy và kiểm tra bộ dữ liệu

```powershell
python -m src.moodle_cloud --config $Config backup
# Lấy CommandId và runner ID từ output, theo dõi tới terminal:
aws ssm get-command-invocation --region $Region --command-id '<CommandId>' --instance-id '<runner-ID>'
```

1. Chọn đúng nguồn, lưu fixture trước backup và thời điểm UTC. Chứng minh writer: web mọi app bị chặn, runtime DB NOLOGIN/connection cũ đã dừng, cron/worker drained và operation lock giữ. App ASG mới cũng bị gate.
2. Thử backup khi task lab hữu hạn đang chạy: phải đợi task hoàn tất/timeout đúng. Không kill task ghi dở rồi đánh dấu nhất quán.
3. SSM phải `Success`, response code 0; prefix S3 có `database.dump`, `moodledata.tar.gz`, `manifest.json` cùng lượt. Manifest upload sau cùng; kiểm SHA-256 cả hai file tải xuống. Manifest một mình không đủ.
4. Manifest medium format 1 lưu source, active artifact, wwwroot, PG major/config references và hashes. Small format 2 có thêm config.php/runtime metadata; không dùng lẫn parser/restore của hai topology.
5. Chờ ít nhất một lịch thật (mặc định backup 02:00 UTC), hoặc cấu hình timer test staging ngắn rồi trả lại. `systemctl start ...service` thủ công không chứng minh timer tự chạy. Lưu journal, S3 timestamp và BackupSuccess; thử missing/failed schedule.
6. Ghi retention: ví dụ giữ 3 set lab đã xác minh đến ngày bàn giao, owner và ngày xóa. Xóa cả version cũ theo runbook, không tự coi expire current object là dọn hết. Trước cleanup ngừng phí, tải bản cuối về kho riêng và kiểm hash, rồi mới xóa cloud.

## 10. Restore medium mới và đo RPO/RTO

Đây là drill, không restore đè nguồn. Tạo project/backend key/DB/EFS/Redis mới, giữ source chạy trong cửa sổ cần so sánh. Điền `restore_source_prefix` đúng site nguồn để IAM đích đọc backup, không ghi vào prefix nguồn. Dùng source artifact được manifest chỉ định; chưa release/seed trên đích.

Nếu bắt đầu từ backup offline sau cleanup: người giữ máy cung cấp riêng `.work/medium-live/private/offline-20261110/`. Kiểm `archive-verified.json`, hash DB/file theo manifest và `runtime-archive.json`; nạp image bằng `docker load --input <moodle-runtime.tar>`, publish lên ECR mới, upload bundle và backup vào S3 mới. Digest/registry cũ trong manifest phải được xử lý theo kiểm tra tương thích của runtime: **không tự sửa manifest để bỏ qua so khớp source image**. N2 cần lập bản phục hồi có kiểm chứng nếu registry/digest đổi; cách đơn giản để chạy drill mới là dựng fixture mới và tạo backup mới có references của môi trường mới. Backup offline chưa được restore-test thì ghi đúng trạng thái đó.

Trên runner **đích**:

```bash
sudo /opt/moodle-medium/operation.sh restore --prefix s3://<backup-bucket>/<source-site>/<timestamp>
# Vẫn maintenance: xem log, manifest/hash và đối chiếu DB/file/URL đích.
sudo /opt/moodle-medium/operation.sh resume --confirm <target-project>-dev-med
```

Trước resume, xác minh account/runner tags, DB/EFS là đích mới, dump compatible PostgreSQL 16/Moodle, đúng source release và hai file đủ/hash đúng. Có endpoint/secret/config riêng của đích, không chép config.php small. Nếu URL đích dài hơn URL nguồn, N2 audit độ dài cột trước khi dùng Moodle replace CLI; không thêm `--shorten` mù hoặc sửa chuỗi trong dump.

Ca âm: copy backup sang **prefix test riêng**, bỏ một file hoặc sửa byte; restore phải từ chối trước khi đè dữ liệu. Ghi trạng thái đích trước/sau. Sau ca âm, dùng đích sạch hoặc phục hồi trạng thái đã xác minh rồi mới thử bộ đúng.

Sau resume:

- Chạy lại LMS-01…06 và checker HTTPS; IDs phải bảo toàn khi restore dump, hash/role/enrolment/submission/grade/feedback đúng.
- Đăng nhập mới rồi thử cùng cookie/file qua hai app; không yêu cầu phiên Redis cũ nguồn sống trên Redis mới.
- Upload/nộp/chấm một dữ liệu mới sau restore để chứng minh quyền ghi, chạy cron và task audit.
- Ghi `T_backup`, `T_sự_cố/drill`, `T_bắt_đầu`, `T_infra_ready`, `T_data_restored`, `T_LMS_verified`. RPO quan sát = tuổi điểm dữ liệu backup tại mốc sự cố/drill; RTO drill = từ bắt đầu phục hồi đến xác minh nghiệp vụ. Ghi rõ có/không tính provision; không đổi thành SLA cam kết.

N2 đã có lượt restore medium độc lập với 47 HTTP checks và bằng chứng node/fixture tại [hồ sơ 09/11](evidence/medium-2026-11-09/README.md); đây là dữ liệu tham khảo, N3 vẫn ký lượt của mình.

## 11. Quan sát, dashboard và cảnh báo

Đã có CloudWatch log/7 alarm trong mã medium. **Chưa có SNS/email action hay dashboard vận hành đầy đủ**; alarm tồn tại/OK không đồng nghĩa đã đạt OBS-02.

1. Đối chiếu log cloud-init, bootstrap, web, operation/cron/backup theo instance/run/time; retention thực tế. Không chia sẻ config hoặc raw SSM output chứa secret.
2. Tạo dashboard: EC2 CPU/credits, RAM/disk từ agent; ALB target health/5xx/latency/request; RDS CPU/connections/storage; Redis CPU/memory/evictions/connections; EFS bytes/throughput; CronSuccess/BackupSuccess. Chốt dimension theo metric thực có, không suy RAM/disk có sẵn từ EC2.
3. Bổ sung/nghiệm thu tín hiệu DB/cache bất thường còn thiếu. Ghi metric, threshold, period, evaluation count, missing data và người nhận. Mã hiện có CronSuccess missing 600 giây, BackupSuccess missing 90000 giây; kiểm phù hợp lịch thật trước test.
4. Phối hợp chủ tài khoản chọn kênh nhận và subscribe/xác thực. Cấu hình alarm action trong IaC hoặc ghi rõ thay đổi ngoài Terraform. Không dùng email giả để ký nhận thông báo.
5. Trên staging dừng một web service hoặc tạo tín hiệu test có kiểm soát. Lưu chuỗi OK → ALARM → thông báo tới nơi nhận → recovery → OK. `set-alarm-state` chỉ chứng minh kênh action, không chứng minh threshold/metric phát hiện lỗi thật.
6. Test mất lịch cron/backup riêng. Đừng đợi một ngày chỉ để thử missing BackupSuccess trên site tốn phí: dùng alarm test ngắn hạn có ghi rõ rồi dọn alarm test/khôi phục lịch. Để `Chờ nghiệm thu` nếu chưa có kênh nhận hoặc chưa đủ thời gian thực nghiệm.

## 12. Đo tải và so sánh small/medium

Dùng [test plan](06-test-plan.md) cho thiết kế và [công cụ small trên mq](https://github.com/iamquan24122006/BTL-Cloud/tree/2d42889/tests/load). Công cụ small mới nằm ở checkout mq, không mặc định có trong khoi. N3 giữ JMX và fixture tương đương, tách profile/URL/credential theo môi trường.

1. Chỉ dùng tài khoản/dataset giả. Tạo test course size S và JMeter plan bằng Moodle generator; cần developer debugging khi tạo, trả về baseline trước đo. Xem `admin/tool/generator/cli/maketestplan.php --help` đúng phiên bản. Không chạy generator vào fixture nghiệm thu duy nhất chưa backup.
2. Mỗi virtual user có tài khoản/session riêng; kiểm login token/CSRF, cookie và assertion đã vào course. HTTP 200 của login/error không tính thành công. Smoke 1–2 user trước, kiểm transaction thực tế và download hash mẫu.
3. Chạy máy phát tải riêng; ghi loại máy/vị trí mạng. Small qua SSM có tunnel, medium qua HTTPS có đường khác: ghi rõ so sánh end-to-end. Không chạy JMeter ngay trên Moodle app/runner.
4. Workload thống nhất: 60% đọc course/nội dung, 20% tải file nhỏ, 10% assignment, 10% login/logout, think time 3–8 giây. Đây là thiết kế của nhóm, ghi JMX thực tế nếu khác.
5. Ma trận: smoke 1–2 user/2 phút; 10 user ramp 2 phút + đo 10 phút; 25 user ramp 3 + đo 10; 50 user ramp 5 + đo 15. Mức dùng kết luận so sánh lặp ít nhất 3 lần; lưu cold/warm cache. Dừng tăng khi lỗi nghiệp vụ kéo dài, mất dữ liệu hoặc backlog nguy hiểm; không ép đạt 50/100/200 user.
6. Medium cố định 2 app cho baseline, tách ca bật scaling policy. Ghi EC2 credit mode **thực tế** từ `describe-instance-credit-specifications` và balance đầu/cuối; không mặc định t3 đang standard từ tài liệu cũ.
7. Thu p50/p95/p99, throughput, mẫu/lỗi theo transaction; CPU/RAM/disk/swap, DB connections, Redis/EFS, ALB và task backlog. Trước/sau test đối chiếu dữ liệu, điểm và file. Không loại lỗi khỏi CSV để đẹp biểu đồ.

```bash
jmeter -n -t .work/n3/<run>/load/moodle.jmx \
  -l .work/n3/<run>/load/run-01.jtl \
  -e -o .work/n3/<run>/load/report-01
```

Output HTML phải là thư mục mới/rỗng. Tham số `-Jusers` chỉ có tác dụng nếu JMX tham chiếu property đó. Raw JTL/CSV/JMX có credential/payload giữ private. Đưa bảng tổng hợp và biểu đồ đã rà soát vào báo cáo.

Ngưỡng nghiên cứu đang đề xuất: p95 trang tương tác ≤3 giây, lỗi nghiệp vụ <1%, không mất dữ liệu và cron không lỗi kéo dài. Nhóm cần chốt ngưỡng trước đo; không coi đây là SLA hoặc kết quả đã đạt. Báo cả lần không đạt và các khác biệt CPU credit/tunnel/cache.

## 13. Sổ chi phí, cleanup và chốt bàn giao

Ghi giờ bắt đầu/kết thúc tồn tại tài nguyên, số lượng/SKU/region, On-Demand estimate, Billing/Cost Explorer lấy lúc nào, credit áp dụng và tiền còn lại. Tổng ngân sách cũ trong các nhánh khác nhau chưa đồng nhất; xác nhận với chủ tài khoản, không coi 100 USD credit ban đầu là số dư hiện tại. Budget là cảnh báo, không tự ngắt chi phí.

Sau thử: backup + checksum + hồ sơ, review saved destroy plan, hủy từng môi trường đúng state. Medium có RDS deletion protection và EFS prevent_destroy; N2 gỡ trong **root cleanup riêng**, chỉ sau chốt dữ liệu cần giữ. Không commit bản gỡ bảo vệ vào root chuẩn. Dọn root medium trước support/backend; giữ state tới khi destroy xong.

Muốn ngừng phí hoàn toàn phải kiểm cả EBS của instance stop, NAT/EIP/IPv4, ALB, RDS và manual/retained snapshots, EFS/Redis snapshots, AMI/EBS snapshot, S3 current + versions/delete markers/multipart, ECR, log groups/alarms/dashboard, secret/KMS/endpoint/budget có tính phí. Không xóa tài nguyên của người khác hoặc region/account chưa xác định. Giữ backup ở máy/kho riêng nếu không muốn trả phí cloud; ghi rõ chưa có bản cloud dự phòng.

Mỗi dòng trong [mẫu kết quả](templates/n3-results.csv) được điền evidence và reviewer. Người khác mở checkout sạch, theo runbook để dựng/xem/demo được. Demo 12–15 phút: kiến trúc và YAML → validate/plan → LMS → cron/backup → restore đã kiểm → số đo tải/chi phí → cleanup. Phần đã quay trước ghi rõ, không destroy/restore nguồn đang demo để minh họa.

Nộp source commit/branch, ma trận yêu cầu, báo cáo, sơ đồ, ảnh/video đã lọc, kết quả raw giữ riêng, manifest/hash và quyền nhận backup/state. Không ký DONE chỉ vì đã upload tài liệu; phải ghi người kiểm tra lại và mọi mục còn `Chờ nghiệm thu`/`Không đạt`.
