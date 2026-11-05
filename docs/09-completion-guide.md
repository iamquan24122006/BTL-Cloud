# Hướng dẫn hoàn tất các phần còn thiếu

## Điểm tiếp tục ngày 05/11/2026

Biên bản mới nhất: [nghiệm thu small](13-small-acceptance.md). CI commit chức năng `6eff8de` đã đạt; ca lỗi thật, smoke và ba baseline 10-user đã có bằng chứng. Hai baseline không lỗi, lượt ba bị tunnel ngắt; chưa đo 25/50-user. GUI/demo, cài tay so sánh, kiểm tra chéo và chốt chi phí/cleanup vẫn mở. Không đánh dấu hoàn tất P0 khi chưa có đủ bằng chứng.

Lab đang dùng là Sydney: `--config config/sydney.yaml`; staging là `--config config/sydney-staging.yaml`. Dev đã đạt kiểm tra chức năng và backup tự động S3. Staging đã đạt nghiệm thu sau restore, ghi file mới và reboot; web/cron/backup timer tự chạy lại. Xem [bằng chứng hiện tại](08-validation.md). Mục Singapore phía dưới là lịch sử, không dùng để chọn lab đích hiện tại.

Việc tiếp theo: nghiệm thu giao diện/demo, đo tải dài hơn và lặp lại có metric, bổ sung kiểm tra failure recovery và hoàn thiện báo cáo/chi phí. JMeter smoke 2 tài khoản chạy lại đã đạt; nguyên nhân lỗi kết nối ở lượt trước chưa xác định. Quyền đọc S3 tạm của staging đã thu hồi sau nghiệm thu; nếu cần diễn tập restore mới, chuẩn bị lại quyền đọc giới hạn đúng bộ backup trước thao tác. Không chạy lại restore để thay thế bước kiểm tra bằng chứng đã có.

**Công cụ và đăng nhập đã sẵn sàng:** người dùng đã cài AWS CLI 2.39.4. Dùng `$env:AWS_PROFILE = 'moodle-project'` trong PowerShell; STS đã xác nhận đúng account Sydney. Nếu terminal cũ chưa nhận PATH mới, mở terminal mới hoặc bổ sung `C:\Program Files\Amazon\AWSCLIV2` vào PATH của phiên. Profile mặc định thuộc account khác, vì vậy phải chọn profile project trước lệnh AWS/Terraform. Hiện không có bước cài đặt hay đăng nhập thủ công đang chặn.

Phần người dùng cần tham gia: kiểm tra giao diện Moodle trên trình duyệt (teacher/student, bố cục, nộp bài, xem điểm) và chụp bằng chứng demo. Bài test HTTP đã có không thay thế đánh giá giao diện. Người vận hành có thể tự động mở tunnel; không cần tự chạy lệnh deploy. Khi phiên AWS hết hạn, người dùng hoàn tất xác thực trên trình duyệt. Không gửi mật khẩu/token qua chat.

Tài liệu dành cho nhóm 4 người, tổng ngân sách dự kiến 400 USD, host Ubuntu Server 26.04. Đây là các việc **cần thực hiện và ghi bằng chứng**, không phải kết quả đã đạt. Mã hiện có chỉ triển khai `small`; `medium` cần phát triển thêm.

Thứ tự: **build runtime → cài tay → deploy small bằng CLI → kiểm tra chức năng → backup/restore → medium → đo tải → báo cáo/demo → cleanup**. Nếu chưa đủ thời gian cho medium, hoàn thành nghiệm thu small và ghi đúng giới hạn trong báo cáo.

**Lab Singapore cũ (lịch sử):** `config/small-new.yaml`, state `.work/moodle-lab-v2-dev/`, từng dừng sau 6 tài nguyên mạng do thiếu `iam:CreateRole`. Không dùng lab này cho thao tác tiếp tục small Sydney. Mẫu `config/dev.yaml` phía dưới cũng là cấu hình lịch sử; dùng Sydney dev/staging tương ứng. Xem [nhật ký AWS](08-validation.md).

## 1. Chia việc và chuẩn bị buổi đầu

| Người | Làm ngay | Sau khi small chạy được |
|---|---|---|
| A | Xác nhận quyền AWS, region, SSM, bucket backup và Terraform | Backend dùng chung, RDS, ALB, ASG |
| B | Build Docker, đọc/cài từng khối trong lab thủ công | EFS, Redis, cấu hình nhiều node |
| C | Kiểm tra CLI/CI, chuẩn bị backup và restore | Release/migration runner, backup nhiều node |
| D | Lập danh sách test, sổ chi phí và bộ dữ liệu giả | JMeter, metric, báo cáo và demo |

Chốt tài khoản AWS thường hay Academy/Learner Lab trước khi chạy. IaC hiện tạo IAM role/profile; nếu lab chỉ cho dùng role được cấp sẵn thì A cần sửa phần IAM và input tương ứng, kiểm thử lại trước deploy. Không dùng quyền AdministratorAccess để che một lỗi IAM.

Nhóm đã xác nhận dùng **AWS thường** ngày 13/10/2026. Vẫn cần kiểm tra phiên đăng nhập, quyền của người deploy và credit thực tế; xác nhận loại tài khoản chưa có nghĩa là đã kết nối AWS.

D giữ sổ chi phí toàn kỳ: 300 USD cho kế hoạch, 100 USD dự phòng. Một môi trường tích hợp dùng chung; staging chỉ tạo khi cần restore. Hạn mức này không phải báo giá AWS. Tra cấu hình theo region trong [AWS Pricing Calculator](https://calculator.aws/) và theo dõi [kế hoạch chi phí](07-report-and-cost.md).

Đặt log thô, plan, backup, JMX/CSV có tài khoản thử trong `.work/` hoặc nơi riêng tư. Chỉ đưa ảnh/log đã loại secret vào báo cáo. Một người apply mỗi lần; không chia sẻ state qua chat hoặc Git.

## 2. Build và kiểm tra Docker — B, C kiểm tra chéo

### Trên máy Windows đang mở repository

Cài và mở Docker Desktop, chọn Linux containers; với backend WSL 2, làm theo [hướng dẫn Windows chính thức](https://docs.docker.com/desktop/setup/install/windows-install/). Không chạy `setup-host.sh` trên Windows: đó là script dành cho EC2 Ubuntu 26.04.

Lệnh kiểm tra tự động đã có, dùng chung cho Windows/Linux và CI:

```powershell
.\.venv\Scripts\python.exe -m scripts.check_runtime
```

Lệnh kiểm tra Docker engine, build image, lint PHP, so sánh PHP CLI/web, thử HTTP và chặn file cấu hình/`.git`. Log và report nằm trong `.work/runtime-check/<run-id>/`; container fixture được dọn sau kiểm tra, image/build cache được giữ. Không publish cổng ra host, không dùng credential, không gọi AWS. Đây là **smoke test runtime với trang PHP mẫu**, chưa cài Moodle hoặc database. Chỉ `status: passed` trong report cùng exit code 0 mới là đạt; lỗi engine/build không được tính là đã kiểm tra ứng dụng. Khi image đã build, có thể dùng `--skip-build` để kiểm tra lại image hiện tại.

Nếu Docker Desktop thoát ngay sau mở, kiểm tra thông báo và điều khoản trong ứng dụng. Docker yêu cầu người dùng chấp nhận điều khoản trước khi tiếp tục; nếu không đồng ý, chọn máy Linux/Docker Engine hoặc CI thay thế. Script kiểm tra không tự chấp nhận điều khoản hay đổi thiết lập Docker.

Trong PowerShell ở thư mục gốc repository:

```powershell
docker version
docker info --format '{{.OSType}}'
docker build --platform linux/amd64 --progress=plain --tag moodle-php:lab scripts
if ($LASTEXITCODE -ne 0) { throw 'Docker build failed; fix it before continuing.' }
docker run --rm --network none --entrypoint php moodle-php:lab -v
docker run --rm --network none --entrypoint php moodle-php:lab -m
docker run --rm --network none --entrypoint apache2ctl moodle-php:lab configtest

$ScriptsPath = (Resolve-Path '.\scripts').Path
foreach ($ScriptName in 'configure.php','install-db.php') {
    docker run --rm --network none --entrypoint php --mount "type=bind,source=$ScriptsPath,target=/scripts,readonly" moodle-php:lab -l "/scripts/$ScriptName"
    if ($LASTEXITCODE -ne 0) { throw "PHP lint failed: $ScriptName" }
}
```

**Đạt khi:** Docker có cả Client và Server, OSType là `linux`, build exit 0, PHP 8.3, Apache `Syntax OK`, hai file PHP không lỗi syntax. Dockerfile đã kiểm tra các extension khi build. Lưu ngày, commit và `docker image inspect --format '{{.Id}}' moodle-php:lab`.

Đây mới là kiểm tra image. `docker run moodle-php:lab` riêng lẻ chưa tạo database, code Moodle, mount hay systemd; không coi nó là lệnh chạy toàn bộ ứng dụng. Ubuntu 26.04 phải được kiểm chứng tiếp trên EC2.

Sau khi smoke test runtime đạt, có thể chạy `python -m scripts.check_moodle` để kiểm tra cài Moodle/PostgreSQL, đăng nhập HTTP, course/file, cron và restore trong Docker cục bộ. Script dùng dữ liệu giả và tự dọn container/volume riêng; log/report nằm trong `.work/moodle-check/`. Xem [phạm vi kiểm thử cục bộ](06-test-plan.md). Kết quả này không thay thế cài tay, cloud-init, systemd, SSM, backup S3 và restore trên EC2 ở các bước tiếp theo.

Nếu không dùng được Docker Desktop, có thể build trên máy Ubuntu của thành viên khác hoặc chạy workflow `.github/workflows/validate.yml` khi đẩy repository lên GitHub. Workflow hỗ trợ push, pull request và workflow_dispatch. Xem từng bước trong Actions; workflow không deploy AWS.

| Lỗi | Xử lý |
|---|---|
| Cannot connect to Docker daemon | Mở Docker Desktop, đợi engine, kiểm tra lại `docker version` |
| Pull timeout/rate limit | Kiểm tra mạng và thông báo Docker Hub; không đổi base image tùy tiện |
| Missing extension/configure failed | Đọc lỗi đầu tiên ở bước RUN; sửa thư viện build/extension tương ứng trong Dockerfile |
| Apache configtest thất bại | Sửa `scripts/moodle-apache.conf`, build lại |
| PHP lint thất bại | Sửa đúng file PHP, lint/build lại rồi chạy kiểm tra liên quan |

## 3. Chuẩn bị AWS và cấu hình — A, D theo dõi chi phí

Máy vận hành cần Python >=3.11, Terraform trong PATH, AWS CLI và [Session Manager plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html). Dùng phiên đăng nhập AWS được cấp; với SSO có thể cấu hình profile rồi đăng nhập. Với Learner Lab, dùng temporary credentials/session token theo hướng dẫn của lớp, không ghi vào YAML/repository.

```powershell
terraform version
aws --version
session-manager-plugin --version
aws sts get-caller-identity
```

Đối chiếu account hiển thị với account nhóm định dùng. Nếu dùng named profile, đặt `$env:AWS_PROFILE` trong terminal này để CLI Python và AWS CLI dùng cùng profile. STS thành công chưa chứng minh đủ quyền EC2/IAM/S3.

Nếu tài khoản có quyền Billing, D tạo Budget và cảnh báo actual/forecast trước khi apply, rồi kiểm tra địa chỉ nhận cảnh báo. Theo dõi tổng kỳ đồ án tại các mốc 200/280/300/340 USD như kế hoạch; nếu kéo dài qua hai tháng phải cộng dồn, không chỉ nhìn budget tháng mới. Budget có độ trễ và không tự bảo đảm dừng mọi tài nguyên ở 400 USD. Learner Lab dùng thêm số credit và cơ chế cảnh báo được tài khoản cho phép.

Trước plan đầu tiên, A tạo bucket backup riêng trong region dự định dùng:

1. Tên bucket duy nhất; Block Public Access bật.
2. Bật default encryption SSE-S3 và versioning.
3. Policy từ chối kết nối không TLS; lifecycle tham khảo trong [runbook S3](05-operations.md).
4. Điền tên bucket thực tế vào `backup_bucket` của `config/dev.yaml`. Không điền tên ví dụ rồi deploy.

Giữ `size: small`, `instance_type: t3.medium`, `volume_gib: 30`, Moodle 4.5.15 và URL localhost như mẫu. Chỉ đổi region khi cả bucket, CLI và Terraform đều dùng cùng region. Không thêm secret hoặc trường YAML tùy ý: CLI từ chối khóa lạ.

Nếu chưa có venv, tạo bằng Python đã cài và cài requirements. Repository trên máy hiện tại đã có `.venv`; dùng lại:

```powershell
$Py = (Resolve-Path '.\.venv\Scripts\python.exe').Path
& $Py -m pip install -r requirements.txt
& $Py -m src.moodle_cloud doctor
& $Py -m src.moodle_cloud --config config/dev.yaml validate
& $Py -m unittest discover -s tests -v
```

Các khối PowerShell tiếp theo dùng biến `$Py` trong cùng terminal. Nếu mở terminal mới, đặt lại biến này. `doctor` chỉ kiểm tra tool, không xác nhận đủ quyền AWS.

## 4. Cài tay rồi dựng small tự động — B và A

### 4.1. Hoàn tất một lần cài thủ công

B theo đúng [lab 03](03-manual-lab.md): EC2 Canonical Ubuntu 26.04, t3.medium, gp3 30 GiB mã hóa, SSM role và SG không inbound. Chuyển manual bundle, chạy từng khối cài đặt, ghi lỗi và cách sửa. D kiểm tra login/course/file/cron theo bước 5 bên dưới.

Máy cài tay nằm ngoài state Terraform; ghi instance ID/tag để tự cleanup. Không giữ máy cài tay và máy tự động chạy lâu cùng lúc. Nếu máy cài tay có dữ liệu cần giữ, backup ra S3 và kiểm tra trước khi xóa.

### 4.2. Dựng máy sạch bằng CLI

A chạy ở Windows:

```powershell
& $Py -m src.moodle_cloud --config config/dev.yaml plan
```

Đọc plan: đúng account/region, AMI Ubuntu 26.04, t3.medium/30 GiB, không inbound SG, IAM chỉ cho phạm vi cần, không tác động tài nguyên ngoài đồ án. Plan chỉ chuẩn bị thay đổi; lệnh sau mới tạo tài nguyên tính phí:

```powershell
& $Py -m src.moodle_cloud --config config/dev.yaml apply --confirm moodle-lab-dev
& $Py -m src.moodle_cloud --config config/dev.yaml status
```

Nếu đổi project/environment, chuỗi confirm phải đổi tương ứng. Nếu source/config thay đổi sau plan hoặc apply lỗi/gián đoạn, tạo plan mới rồi đọc lại. Không sửa source và giữ saved plan cũ.

Lấy instance ID từ status, kiểm tra SSM online và kết nối. Ví dụ với region mẫu:

```powershell
$InstanceId = Read-Host 'Instance ID cua small dev'
aws --region ap-southeast-1 ssm describe-instance-information
aws --region ap-southeast-1 ssm start-session --target $InstanceId
```

Trong **SSM shell trên EC2**:

```bash
sudo cloud-init status --wait
sudo tail -n 80 /var/log/cloud-init-output.log
sudo /opt/moodle-distribution/health.sh
sudo /opt/moodle-distribution/php-cli.sh -v
sudo systemctl start moodle-cron.service
sudo journalctl -u moodle-cron.service --no-pager -n 50
sudo docker logs --tail 50 moodle-web
```

**Đạt khi:** cloud-init không lỗi, health pass, PHP/DB đúng phiên bản, cron kết thúc thành công. Terraform apply thành công chưa đủ. Nếu health lỗi, kiểm tra journal `moodle-web.service`, log cài, quyền dataroot và kết nối DB; không lặp migration để né lỗi cài dở.

## 5. Mở Moodle và kiểm tra nghiệp vụ — D, B sửa lỗi

Mở **PowerShell mới ở thư mục repository**, tạo file tham số để tránh lỗi escape JSON. Đặt instance ID đúng máy cần mở:

```powershell
$InstanceId = Read-Host 'Instance ID can mo Moodle'
New-Item -ItemType Directory -Force .work | Out-Null
'{"portNumber":["8080"],"localPortNumber":["8080"]}' | Set-Content -Encoding ascii .work/ssm-ports.json
aws --region ap-southeast-1 ssm start-session --target $InstanceId --document-name AWS-StartPortForwardingSession --parameters file://.work/ssm-ports.json
```

Giữ terminal này mở. Truy cập **http://localhost:8080**. Đây là đường hầm SSM; không cần mở cổng 22/80/8080 trên SG. [Cách dùng port forwarding](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html)

Trong phiên SSM shell riêng, đọc `sudo cat /root/moodle-initial-admin.txt` ở chế độ riêng tư, không chụp/ghi log màn hình. Đăng nhập rồi đổi mật khẩu và email admin.

Thực hiện lần lượt:

1. Tạo course `Cloud Lab`, tài khoản teacher và student giả; enrol đúng vai trò.
2. Teacher upload file mẫu, student tải về. Trên Windows, dùng `Get-FileHash -Algorithm SHA256` cho file gốc và file tải về; phải trùng hash.
3. Student nộp bài, teacher xem/chấm; kiểm tra user không có quyền không truy cập bài của người khác.
4. Chạy cron, kiểm tra journal và trang Scheduled tasks có lần chạy thành công.
5. Kiểm tra `/.git/config` và `/config.php` qua tunnel bị chặn; không lộ mã/secret.
6. Trên staging sau này, reboot EC2 và kiểm tra web/cron tự lên, login/file vẫn hoạt động.

**Bằng chứng:** ảnh nghiệp vụ, hash file, log health/cron đã lọc, thời điểm và phiên bản. Ghi pass/fail từng mục F01–F13 trong [test plan](06-test-plan.md). Không đánh dấu các mục chưa chạy.

## 6. Backup và restore sang máy mới — C, D đối chiếu

### 6.1. Backup nguồn

Tạo trước một dữ liệu dễ nhận dạng: tên course, một học viên giả, một bài nộp và một file đã lưu SHA-256. Trong SSM dev:

```bash
sudo /opt/moodle-distribution/backup.sh
sudo /opt/moodle-distribution/health.sh
```

Hoặc dùng CLI `backup` ở Windows, rồi đọc trạng thái SSM command như [runbook 05](05-operations.md). Command ID chỉ là đã gửi yêu cầu.

**Đạt khi:** lệnh hoàn tất, site mở lại, S3 có một set gồm dump, archive, config, code/runtime metadata, checksum và manifest. Ghi URI chính xác. Backup chỉ nằm trên EC2 chưa đáp ứng yêu cầu phục hồi khi mất máy.

### 6.2. Dựng staging và phục hồi

Trong Windows, nếu chưa có cấu hình staging, copy mẫu; nếu đã có thì mở sửa, không ghi đè:

```powershell
if (Test-Path config/staging.yaml) { throw 'staging.yaml already exists; edit it instead of overwriting.' }
Copy-Item config/staging.example.yaml config/staging.yaml
# Sua region va backup_bucket cho dung; environment giu la staging.
& $Py -m src.moodle_cloud --config config/staging.yaml validate
& $Py -m src.moodle_cloud --config config/staging.yaml plan
# Doc plan, sau do:
& $Py -m src.moodle_cloud --config config/staging.yaml apply --confirm moodle-lab-staging
& $Py -m src.moodle_cloud --config config/staging.yaml status
```

Chờ staging cài hoàn tất và health pass trước khi restore. A cấp tạm quyền `s3:GetObject` cho role staging trên đúng set nguồn; mặc định Terraform chỉ cho ghi prefix của chính môi trường nên staging chưa đọc được backup dev.

Thực hiện **mục 4 của [runbook 05](05-operations.md)** trên staging mới: tải set, kiểm tra checksum/commit/runtime, dừng writer, khôi phục DB và moodledata, purge cache, tắt maintenance, mở web. Các lệnh thay DB chỉ dùng cho staging đã xác nhận, không chạy vào dev.

Giữ `config.php` staging với mật khẩu DB mới; không chép config nguồn đè lên. Đóng tunnel dev, mở tunnel staging với cùng local port 8080. Đăng nhập bằng tài khoản có trong backup nguồn, không dùng mật khẩu khởi tạo của staging sau restore.

**Đạt khi:** course/user/enrolment/bài nộp khớp, tải file ra đúng hash, health/cron pass và tạo được bài nộp mới. Ghi thời gian bắt đầu/kết thúc, backup timestamp, lỗi và cách sửa. Gỡ quyền đọc S3 tạm sau khi xong. Có dump/checksum nhưng chưa phục hồi thành công thì chưa đạt G3.

## 7. Viết phần medium — A/B/C, chỉ sau khi small phục hồi được

Đây là phần **chưa có mã**, không có lệnh apply medium dùng ngay. Không đổi `size: medium` trong YAML hiện tại; CLI sẽ từ chối. Giữ small làm baseline và triển khai medium ở môi trường riêng.

### Các thay đổi cần viết, theo thứ tự tích hợp

| Thứ tự | Việc phải bổ sung | File/module cần tạo hoặc sửa | Kiểm tra trước khi chuyển tiếp |
|---|---|---|---|
| 1 | Backend dùng chung, khóa state; schema/config cho medium | CLI, backend, mẫu YAML, tests | State dev/staging riêng, không có hai apply ghi cùng state |
| 2 | VPC hai AZ, public ALB, private app/DB và egress | `infra/modules/network`, `infra/medium` | Route, SG, SSM và egress đúng; app/DB không public IP |
| 3 | RDS PG16 Single-AZ và secret, một app thử nghiệm | database module, cấu hình PHP | DB chỉ nhận từ app/cron SG; role app riêng, TLS và login/course pass |
| 4 | EFS mount TLS và ownership thống nhất | storage module, host/bootstrap | Hai node UID/GID giống nhau; ghi qua A, đọc qua B |
| 5 | Redis session và MUC | cache module, Dockerfile, Moodle config/MUC | PHP Redis extension có thật; TLS/auth theo endpoint; login giữ khi đổi node |
| 6 | ALB HTTPS, DNS/ACM, app listener riêng | loadbalancer module, Apache/config.php | HTTPS/redirect/file hoạt động; app chỉ nhận từ ALB; hai target healthy |
| 7 | AMI/image dùng chung, ASG 2 node, cron/release runner | compute module, pipeline | Node mới tự ready; migration chỉ một runner; thay node không mất state |
| 8 | Backup nhất quán nhiều node, restore, log/alarms | scripts mới, observability module | Restore toàn bộ ứng dụng; alarm thực sự phát tín hiệu thử nghiệm |

Các đường dẫn module trong bảng là **đề xuất cần tạo**, chưa phải module tồn tại. Xem hợp đồng input/output và ma trận SG trong [kiến trúc 02](02-architecture.md).

Những giả định single-node phải sửa rõ ràng:

- `src/moodle_cloud.py`: đang dùng root Terraform small và backend local. Thêm chọn root theo preset, validate endpoint/domain/certificate, state và chốt plan/account riêng cho medium; giữ test từ chối input sai.
- `scripts/configure.php`: đang hard-code DB `127.0.0.1` và URL localhost. Medium cần endpoint RDS, secret runtime, dataroot EFS, cache local, Redis và thiết lập proxy đúng cấu trúc ALB.
- Apache đang nghe loopback và `Require local`: ALB không kết nối được. Tạo cấu hình medium riêng nghe private interface/port cần thiết, kèm SG chỉ nhận ALB; không sửa cấu hình small đang dùng.
- `bootstrap.sh`: đang cài PostgreSQL local, cài schema và bật cron trên mọi máy. App medium chỉ nhận release/config, mount storage rồi phục vụ; install/upgrade chuyển sang release job có khóa; cron chạy trên runner riêng.
- Dockerfile hiện chưa có Redis extension. Ghim phiên bản extension phù hợp, kiểm tra kết nối thực tế. Redis session handler và mapping MUC là hai việc riêng; cài extension chưa tự bật cả hai. [Moodle Redis cache](https://docs.moodle.org/405/en/Redis_cache_store)
- `backup.sh` chỉ dừng một web node và cron local. Medium cần chặn ghi ở toàn bộ app/runner, xác nhận mọi writer đã dừng, chụp DB/file cùng cửa sổ nhất quán rồi mở lại. Không dùng nguyên script small và coi là backup cluster.
- Backup metadata chưa chứa image layers: khi dùng ASG, build/publish image hoặc AMI một lần và cho mọi node dùng cùng artifact; ghi định danh artifact vào manifest. Tính phí lưu artifact vào dự toán.

Với Terraform >=1.10 có thể dùng S3 backend và `use_lockfile = true`; bucket mã hóa/versioning, quyền state/lock giới hạn và key khác nhau theo môi trường. Backend không nhận secret qua YAML. Cần sửa CLI đang ép backend local trước khi migrate state; sao lưu state và theo [tài liệu HashiCorp](https://developer.hashicorp.com/terraform/language/backend/s3).

Trước ALB HTTPS, nhóm cần domain kiểm soát được và chứng chỉ ACM đã xác thực trong region ALB. Trước apply medium, D lập estimate theo SKU/region thật, tính giờ NAT/ALB/RDS/cache/EBS/IP và khoản còn lại sau dự phòng. Bắt đầu ASG min/desired 2, max 3 theo kế hoạch. RDS/cache Single-AZ giúp giới hạn lab, chưa tạo HA toàn hệ thống.

**Bài nghiệm thu medium:** hai target phục vụ thật; login còn hiệu lực khi đổi node; file upload từ A tải được ở B; loại một app rồi ASG thay thế; cron không bị khởi tạo trên mọi app; restore ra môi trường mới. Ghi node ID qua log/SSM nội bộ, không tạo debug endpoint public lộ metadata.

## 8. Kiểm thử tải — D, A/B quan sát tài nguyên

Chỉ dùng staging và tài khoản giả. Cài JMeter trên máy phát tải riêng, theo [hướng dẫn JMeter](https://jmeter.apache.org/usermanual/get-started.html). Tạo course và test plan bằng công cụ Moodle; generator yêu cầu cấu hình phát triển phù hợp và không dành cho site live. [JMeter generator của Moodle](https://docs.moodle.org/405/en/JMeter_test_plan_generator)

1. Tạo dataset cố định; sinh JMX/CSV user. Sau tạo dữ liệu trả debugging về mức baseline trước khi đo.
2. Chạy 1 user, kiểm tra login/token/cookie, assertion thấy nội dung course và nghiệp vụ thành công. HTTP 200 riêng lẻ không đủ.
3. Chuẩn bị lần lượt 10, 25, 50 user đồng thời, think time 3–8 giây và ramp-up như [test plan 06](06-test-plan.md). Chỉnh thread group/biến thật sự được JMX sử dụng; không giả định `-Jusers` tự có tác dụng.
4. Lặp tối thiểu 3 lần/cấu hình nếu thời gian cho phép, giữ dataset/workload nhất quán; đặt tên run riêng. Nếu lỗi tăng kéo dài, dừng tăng tải và tìm nguyên nhân.

Ví dụ PowerShell sau khi đã tạo và kiểm tra JMX:

```powershell
jmeter -n -t .work/load/moodle.jmx -l .work/load/run-01.jtl -e -o .work/load/report-01
```

Output report phải mới/rỗng. Ghi p50/p95/p99, throughput, lỗi nghiệp vụ, CPU/RAM/disk, DB và cron. Với T3 standard phải ghi CPUCreditBalance đầu/cuối. Small qua SSM đo cả độ trễ đường hầm/máy phát tải; không diễn giải thành năng lực EC2 riêng biệt.

**Đầu ra:** JTL/JMX riêng tư, HTML report, bảng tổng hợp đã bỏ dữ liệu nhạy cảm, biểu đồ và nhận xét điểm nghẽn. Không điền số mục tiêu vào cột kết quả thực nghiệm.

## 9. Hoàn thiện báo cáo và demo — cả nhóm, D tổng hợp

Mỗi người viết phần mình triển khai. D ghép theo [dàn ý báo cáo](07-report-and-cost.md): bài toán → thiết kế → cài đặt → thực nghiệm → đánh giá → giới hạn.

Bộ bằng chứng tối thiểu:

- Lần cài tay và lần dựng sạch bằng CLI: commit, phiên bản, AMI, thời gian, lỗi và cách sửa.
- Bảng test chức năng có pass/fail và đường dẫn ảnh/log tương ứng.
- Một restore drill thành công, checksum file và thời gian phục hồi; phân biệt RTO với tuổi dữ liệu backup/RPO.
- Kết quả tải và điều kiện đo; so sánh cấu hình chỉ khi cùng workload/dataset.
- Calculator estimate có ngày tra cứu và chi phí thực tế/credit đã ghi nhận, kèm tài nguyên còn lưu.
- Video hoặc log quá trình provision; demo live login/course/file/cron/backup/restore trong 12–15 phút.

Mô tả small/medium đúng phần đã chạy. Large, HA, nâng cấp tự động và plugin còn thiếu phải ghi là hướng phát triển. Khi hoàn thành một cổng, cập nhật trạng thái ở `00-project-plan.md` và `08-validation.md` kèm bằng chứng, không chỉ đổi nhãn thành “đã xong”.

## 10. Cleanup và chốt bàn giao — A/C, D kiểm kê

Sau khi đã lưu bằng chứng và kiểm chứng backup ở ngoài EC2, chạy từng môi trường riêng:

```powershell
& $Py -m src.moodle_cloud --config config/staging.yaml plan --destroy
# Doc destroy plan va xac nhan staging khong con du lieu can giu:
& $Py -m src.moodle_cloud --config config/staging.yaml destroy --confirm moodle-lab-staging --allow-data-loss

& $Py -m src.moodle_cloud --config config/dev.yaml plan --destroy
# Chi xoa dev sau khi backup/restore va bang chung da du:
& $Py -m src.moodle_cloud --config config/dev.yaml destroy --confirm moodle-lab-dev --allow-data-loss
```

Không copy cả khối rồi bỏ qua bước đọc plan. EC2 small bị hủy sẽ mất root EBS, DB, moodledata và backup local. Bucket S3 riêng vẫn còn và tiếp tục tính phí. Xóa máy cài tay riêng; kiểm kê cả volume/snapshot/IP/log/artifact và medium nếu đã tạo. Không xóa state trước khi xử lý hết tài nguyên.

**Project đạt P0 khi:** cài tay, deploy tự động, chức năng, restore, tải và hồ sơ bàn giao đều có bằng chứng. **Đạt mục tiêu P0 + P1 khi:** thêm đủ các bài nghiệm thu medium ở bước 7. Build/test local hoặc Terraform apply riêng lẻ chưa đủ để chốt hoàn thành.
