# Nhật ký kiểm chứng repository

## Tiếp tục tích hợp khoi ngày 14/11/2026

Đã đối chiếu PR #2 merged ngày 12/11, cả hai CI tại head `8397e72` và CI merge commit master `699dfc6` đều success. Khoi có thêm commit `2440d08` (13/11), được ghép tiếp trên master: lựa chọn builder t3.small, kiểm tra canary namespace khác khi purge MUC và hồ sơ N3/offline. Đưa patch tạo thư mục cha load runner trong hồ sơ N3 vào source thực tế; không thay cơ chế thư mục kết quả độc quyền.

Chạy lại **89 unit test đạt**; Terraform fmt, init backend=false/validate medium_builder với provider 6.72.0 và Bash syntax load runner đạt. Không gọi AWS apply/restore/destroy. CI đầy đủ của bản cập nhật kiểm chứng runtime small/medium và canary mới. Kết quả tải N3 thuộc account riêng: đủ lượt/user/thời lượng và không lỗi nghiệp vụ, nhưng 50-user r2/r3 không đạt ngưỡng p95 tương tác 3 giây. Không sửa evidence để đổi kết quả này hoặc gộp với phép đo Sydney cũ.

## Tích hợp Small và Medium ngày 12/11/2026

Hợp nhất small trên master `b1bcbe2` và medium từ khoi `82e95c9`, giải quyết xung đột CLI, manual bundle, CI và tài liệu. **89 unit test đạt**; validate hai YAML, compile Python, sinh bundle small/medium, Bash syntax và Terraform fmt đạt. Giữ default Sydney, state small, health/backup/restore/command-status và data-loss guard; ghép schema/backend/runner medium và snapshot saved plan chống re-plan đồng thời. Regression kiểm tra routing preset/account/prefix; công cụ acceptance small từ chối YAML medium trước khi gọi AWS.

CI cũ của khoi thất bại khi teardown mock EFS do `prevent_destroy`, dù các assertion đã đạt. Mock tests medium chuyển sang plan với ID EFS/access point và Redis endpoint có giá trị tại plan, không gỡ bảo vệ tài nguyên thật. Hai mock test đã chạy lại đạt trong root test riêng dùng AWS provider 6.67.0 sẵn có; provider 6.72.0 theo lockfile nguồn được kiểm trên CI. Lượt CI tích hợp đầu tiên đã qua runtime/restore small và các root small/backup/budget/load, phát hiện thiếu computed mock values cho assertion user-data; đã bổ sung các defaults này. Workflow tích hợp giữ đầy đủ runtime/restore và Terraform checks của cả small và medium. Kết quả CI cuối cần đối chiếu GitHub Actions/PR tương ứng; kiểm tra local không chứng minh deploy AWS mới. Không chạy apply/restore/destroy AWS trong lượt hợp nhất. Xem [hợp đồng bản tích hợp](17-small-medium-integration.md).

## Tiếp tục Small ngày 08/11/2026

Unit test chạy lại bằng Python có PyYAML: **63/63 đạt**, không gọi AWS thật. Đối chiếu local summaries thấy smoke 2 user, ba lượt 10 user, ba lượt 25 user và hai lượt 50 user đều `passed`, 0 lỗi. Hai lượt 50 user có Course p95 414/401 ms; chưa có summary r3 cục bộ, chưa xác nhận toàn ma trận/metric/cleanup. STS và SSM báo phiên `moodle-project` hết hạn; AWS CLI hiện 2.39.4. Không thay đổi hạ tầng AWS trong bước đối chiếu này.

Bổ sung kịch bản demo 12–15 phút, ma trận dịch vụ thực tế và helper PowerShell mở SSM tunnel có kiểm tra account/instance/SSM/cổng 8080. Helper dùng JSON parameter file để tránh lỗi quote PowerShell; không tự login/apply/restore. Kiểm tra parser PowerShell và `git diff --check` đạt. Việc mở tunnel và GUI cần phiên AWS hợp lệ; kết quả local không thay thế kiểm chứng trên cloud. Trạng thái hiện hành ở [biên bản small](13-small-acceptance.md).

## Thử lỗi và chuẩn bị bàn giao small ngày 05/11/2026

Xem [biên bản small](13-small-acceptance.md) để đối chiếu các tiêu chí đã đạt và còn chờ. Bổ sung bằng chứng AWS thật cho web dừng/recovery, backup bị S3 `AccessDenied` và restore thiếu/hỏng bị từ chối trước ghi đè: `.work/moodle-sydney-staging/commands/20261105T074342Z-10ef3c/result.json`, SSM `Success`, exit 0. Nghiệp vụ sau ca lỗi đạt.

Đã tạo 50 tài khoản giả trên staging, không xuất password ra log; PHP lint và seeding thành công trong `.work/moodle-sydney-staging/commands/20261105T075428Z-50432c/result.json`. Đã thêm generator workload `moodle-small.jmx` và sampler OS/DB. Smoke workload mới gặp hai `NoHttpResponseException`; biến thể không keep-alive chưa chạy được do Windows từ chối tạo tiến trình ngoài sandbox (`Access is denied`, OS error 5). Browser control cũng tự dừng vì không xác minh được URL Chrome; không có bằng chứng nghiệm thu GUI mới. Đã mở đăng nhập GitHub theo xác nhận người dùng, chưa xác nhận phiên đăng nhập hoặc CI mới thành công.

Kiểm tra cục bộ mới nhất: **58 unit test đạt**, Python compileall đạt và `git diff --check` đạt. Tests mới kiểm tra CPU theo delta, DB counts và không đưa stderr riêng tư vào metric. Các kiểm tra này không thay thế phép đo tải/GUI/CI còn thiếu. Số liệu Cost Explorer có ngày Estimated và không có service group, chưa dùng làm hóa đơn small bằng 0.

## Hoàn tất kiểm chứng backup/restore và reboot staging ngày 05/11/2026

Phần này cập nhật trạng thái sau khi người dùng cài AWS CLI và xác nhận đăng nhập. AWS CLI 2.39.4 đã hoạt động. STS ngoài sandbox xác nhận profile `moodle-project` đúng account của lab Sydney; profile mặc định thuộc account cũ được giữ nguyên. Lượt gọi trong sandbox không thấy credential, nên không dùng kết quả đó để suy luận rằng máy không có profile AWS.

| Hạng mục | Kết quả và bằng chứng riêng tư trong `.work/` |
|---|---|
| EC2/SSM | Dev và staging cùng `running`, đúng tag môi trường; cả hai SSM `Online` |
| Backup S3 nguồn | Hai bộ đầy đủ: `moodle-sydney-dev/20261105T011621Z/` và `moodle-sydney-dev/20261105T020000Z/`. Tải bộ đầu về staging, xác minh đủ 8 file, checksum, archive an toàn, commit Moodle, Dockerfile và `pg_restore --list`: đạt. `moodle-sydney-staging/commands/20261105T072851Z-c531ac/result.json` |
| Lệnh restore trước đó | Thu lại invocation đã hoàn tất từ SSM: bắt đầu 07:03:24 UTC, kết thúc 07:04:28 UTC, `Success`, exit 0, elapsed 64,496 giây. Đây là thời gian thực thi lệnh, không phải RTO toàn quy trình. `moodle-sydney-staging/recovered-restore-result.json` |
| Nghiệp vụ sau restore | `passed`: admin/student/studentb/teacher login, logout, enrolment/role, course/file đúng hash, bài nộp/điểm/phản hồi và chặn truy cập sai quyền. `moodle-sydney-staging/acceptance/20261105T073000Z-0719bbd1/report.json` |
| Ghi dữ liệu mới sau restore | Tạo và đọc lại file trên staging thành công; 0 scheduled task đang bật có faildelay, 0 adhoc task có faildelay. Bật lại backup timer sau nghiệm thu. `moodle-sydney-staging/commands/20261105T073116Z-d6478b/result.json` |
| Backup/cron dev thực chạy | Backup timer kích hoạt 02:00 UTC, service hoàn tất 02:00:19 UTC với `Result=success`, exit 0; S3 có bộ file tương ứng. Web/cron/backup timer active, không có task faildelay. `moodle-sydney-dev/commands/20261105T073128Z-c78c31/result.json` |
| Reboot staging | Boot ID đổi từ `eb5dd560-480c-4bf0-8751-c8b4ee1fe932` sang `14db9234-ecf2-432e-acd9-ef663fa3c01f`; cloud-init done; web, cron timer, backup timer active. Chạy lại toàn bộ nghiệp vụ vẫn đạt và không có task faildelay. `moodle-sydney-staging/commands/20261105T073346Z-c6490d/result.json` |
| Thu hồi quyền tạm | Đối chiếu nội dung rồi xóa đúng inline policy `moodle-temporary-restore` khỏi role staging, kiểm tra policy đã vắng mặt; giữ policy ghi backup. `moodle-sydney-staging/restore-policy-cleanup.json` |

Không chạy restore lần nữa: kiểm tra đích phát hiện dữ liệu đã phục hồi và thư mục `before-restore-20261105T070333Z-67778`; log SSM xác nhận lần restore trước thành công. Lần kiểm tra sơ bộ đầu tiên dừng ở backup timer inactive, đúng trạng thái script restore chủ động giữ trong khi chờ nghiệm thu; lượt kiểm tra sau đã hoàn tất và timer được bật lại.

Trong kiểm tra reboot, API AWS thành công nhưng helper CLI cố parse body rỗng thành JSON nên báo lỗi cục bộ. Đã kiểm tra boot ID và health thay vì gửi reboot lại. Sửa `aws()` để chấp nhận body rỗng chỉ khi subprocess thành công, vẫn từ chối JSON lỗi không rỗng. Thêm hai regression test; toàn bộ **56 unit test đạt**, `git diff --check` đạt. Dòng `restore_tested: false` trong manifest backup gốc được giữ nguyên; bằng chứng restore nằm ở các report độc lập phía trên.

Không tạo thêm EC2, bucket hoặc dịch vụ trong lượt này. Hai EC2 hiện vẫn chạy. Còn nghiệm thu bằng trình duyệt/ảnh demo, đo tải có metric và lặp lại, kiểm tra failure recovery, cài tay theo rubric và hoàn thiện báo cáo/chi phí. Chưa triển khai medium/large và chưa có bằng chứng GitHub Actions chạy thành công. Reboot đã kiểm chứng trên staging, không suy rộng thành đã reboot dev.

## Cập nhật ngày 05/11/2026: Sydney và lượt tiếp tục

Môi trường hiện tại dùng `config/sydney.yaml` (`moodle-sydney-dev`, `ap-southeast-2`) và `config/sydney-staging.yaml`. Các phần Singapore ngày 29/10 bên dưới là lịch sử của lab khác, không mô tả trạng thái Sydney.

| Kiểm tra | Bằng chứng và kết luận |
|---|---|
| Nghiệm thu chức năng EC2 dev | Report `.work/moodle-sydney-dev/acceptance/20261105T011940Z-b12ff8cb/report.json`: `passed`, SSM response code 0; login admin/student/studentb/teacher, logout, course/file, enrolment/role, submission/grade, chặn đọc bài riêng và file ẩn danh |
| Runtime EC2 trong report | Moodle 4.5.15, PHP 8.3.35, PostgreSQL 16.15 |
| Khởi tạo staging | `.work/moodle-sydney-staging/commands/20261105T070124Z-9da01e/result.json`: cloud-init `done`, không có lỗi; basic health đạt. Đây chưa phải kiểm tra restore |
| Unit test chạy lại | 54 tests đạt, `python -m unittest discover -s tests -v`; dùng Python MSYS trong `.work/implementation-venv/bin/` và PyYAML sẵn có từ site-packages của `.work/validation-venv/` qua `PYTHONPATH` |
| HTTP qua tunnel hiện có | Trang `/login/index.php` trả HTTP 200 trong lượt tiếp tục |
| Đọc với hai tài khoản | `.work/load/sydney-python-resume-20261105/summary.json`: `passed`, 19 samples, 0 lỗi; thời lượng yêu cầu 60 giây, ramp 5 giây, tổng 70,297 giây gồm đăng nhập/đăng xuất; 9 course, 2 download; SHA-256 đúng và file riêng bị chặn sau logout |
| JMeter trước đó | `.work/load/sydney-smoke-v3-summary.json`: `failed`; 1/5 Download lỗi `NoHttpResponseException`. Lượt Python đạt không xóa bỏ lỗi của JMeter |
| JMeter chạy lại | `.work/load/sydney-resume-jmeter-v2-20261105-summary.json`: `passed`, 2 tài khoản, duration 60 giây, ramp 10 giây; 8 Course + 8 Download đều đạt, 2 Login đạt. Chạy ngoài sandbox; lượt chạy trong sandbox bị ngắt trước khi bắt đầu workload, không tính là đạt |

Lượt đọc hai tài khoản là smoke test qua SSM tunnel, không chứng minh sức tải, không thay thế đo dài/lặp lại kèm CPU credits, metric máy chủ và workload đầy đủ. Chưa xác nhận nguyên nhân lỗi kết nối JMeter.

Đã tìm thấy state Terraform của dev, staging và bucket backup ở Sydney, nhưng sự tồn tại state không chứng minh backup S3 đã hoàn tất hoặc khôi phục thành công. Còn phải kiểm tra backup set, restore sang staging, so sánh dữ liệu và chạy lại nghiệp vụ; kiểm tra reboot, lịch backup/cron và dọn quyền đọc nguồn tạm nếu có.

AWS CLI không được tìm thấy trong PATH hoặc vị trí cài chuẩn trong môi trường shell của lượt tiếp tục. Đã tải bộ cài chính thức vào `.work/tools/AWSCLIV2.msi`, Authenticode `Valid`, signer Amazon Web Services. Cài silent trả exit code 1603; log `.work/tools/awscli-install.log` xác định lỗi 1925: thiếu quyền Administrator để cài cho toàn máy. Người dùng cần chạy bộ cài và duyệt UAC. Chưa gọi lại STS/inventory AWS trong lượt này; không suy ra phiên đăng nhập đã hết hạn hay cần cấp lại IAM. Chưa thay đổi hạ tầng AWS.

Chuẩn bị trong phiên làm việc 07–08/10/2026, sau đó cập nhật theo Ubuntu Server 26.04. Đã kết nối AWS và thử triển khai lab mới ngày 29/10/2026 (UTC); tiến độ và lỗi quyền IAM nằm ở phần cuối tài liệu.

## Đã kiểm tra cục bộ

| Kiểm tra | Kết quả |
|---|---|
| Python `unittest discover -s tests -v` | 19 tests đạt, gồm nhiều trường hợp đầu vào không hợp lệ |
| CLI validate cấu hình dev | Đạt, không gọi AWS |
| Sinh manual transfer bundle | Đạt; 12 file giải mã khớp đầu vào, bundle chưa cài server |
| Python compileall | Đạt |
| Bash syntax | 6 script và manual-transfer bundle đạt sau đổi runtime |
| Terraform fmt | Đạt |
| Terraform init backend=false | Đạt, provider hashicorp/aws 6.67.0 |
| Terraform validate | Đạt; các plan giả lập cuối cũng hợp lệ |
| Terraform mock tests | 2 kịch bản đạt; không gọi AWS thật |
| Provider lock đa nền tảng | Checksum Windows amd64 và Linux amd64 đã ghi vào lockfile |
| Liên kết nội bộ Markdown | 11 file kiểm tra, không có liên kết bị hỏng sau bổ sung hướng dẫn hoàn tất |
| Workflow YAML và line endings | Parse được YAML; các script dùng LF |
| PowerShell trong hướng dẫn hoàn tất | 10 khối lệnh parse thành công; không thực thi các lệnh deploy/cleanup |
| Tham số Moodle install_database.php | Đã đối chiếu mã nguồn tag v4.5.15 chính thức |
| Nguồn package Ubuntu 26.04 | Trang chính thức có docker.io, docker-buildx, awscli; PHP mặc định 8.5 |
| Nguồn PostgreSQL | PGDG công bố hỗ trợ resolute; chưa chạy apt install trên máy thật |
| Base image PHP | Đã ghim digest; build và smoke test đạt ngày 29/10/2026, xem kết quả bên dưới |

Runtime kiểm tra: Python 3.12, PyYAML 6.0.2, Terraform 1.13.4 trên Windows. Terraform zip tải từ HashiCorp, checksum SHA-256 đã đối chiếu file phát hành. Trong lượt kiểm tra Ubuntu 26.04, sandbox chặn thư mục tạm của Python, provider Terraform không phản hồi và Git Bash bị chặn khởi động. Đã chạy lại các kiểm tra tương ứng ngoài sandbox với quyền được cho phép: 19 unit test, 2 mock test Terraform và kiểm tra Bash đều đạt. Không gọi AWS thật.

Khi chạy thử đầu tiên, test SG phát hiện thuộc tính ingress chưa xác định ở bước plan. Đã sửa cấu hình thành `ingress = []` và cả hai mock test đạt. Khi rà soát backup, đã sửa chờ cron để tính cả trạng thái `activating` của systemd oneshot. Bundle chuyển file dùng base64 theo dòng ngắn để phù hợp paste qua terminal.

Thay đổi Ubuntu 26.04 gồm AMI, host setup PGDG/Docker, PHP 8.3 container, image ID dùng chung cho mọi runner, systemd web/cron và metadata runtime trong backup format 2. Runbook cài tay, restore và CI đã được sửa tương ứng. Đối chiếu nguồn tại [ADR phiên bản](01-version-decisions.md), [gói Docker](https://packages.ubuntu.com/resolute/docker.io), [Buildx](https://packages.ubuntu.com/resolute/docker-buildx) và [AWS CLI](https://packages.ubuntu.com/resolute/awscli).

## Kiểm tra runtime Docker ngày 29/10/2026

Đã chạy `python -m scripts.check_runtime` trên Docker Desktop với Linux engine `linux/x86_64`, ngoài sandbox Windows để truy cập được Docker. Lượt hoàn tất có exit code **0**, report **`status: passed`**, bắt đầu `2026-10-29T10:03:53Z`, kết thúc `2026-10-29T10:05:43Z`. Lượt trước bị ngắt khi build chưa hoàn tất; không tính là đạt.

| Kiểm tra | Kết quả |
|---|---|
| Build `moodle-php:lab` từ Dockerfile đã ghim | Đạt |
| Lint `configure.php`, `install-db.php` | Đạt |
| PHP CLI và web | Cùng PHP 8.3.35, `max_input_vars=5000`, đủ 13 extension được kiểm tra |
| Apache configtest và HTTP fixture | `Syntax OK`, HTTP 200 |
| `/config.php`, `/.git/config` | Cả hai trả HTTP 403 |
| Mã ứng dụng mount chỉ đọc | Đạt |
| Dọn container fixture | Đạt, exit code 0 |
| Unit test script kiểm tra runtime | 4 tests đạt |

Bằng chứng cục bộ: `.work/runtime-check/20261029T100353Z-31ebff2d/report.json` và các log cùng thư mục. Image ID: `sha256:b1a65d2bd87a00b73d866ff31175bc7704ea0e189cd2e5fae66d1240cb2d3c03`. Image và build cache được giữ để dùng lại; thư mục `.work/` không được commit.

Đây là smoke test PHP/Apache với trang PHP mẫu; chưa kiểm chứng cài Moodle, PostgreSQL, systemd, AWS hoặc backup/restore.

## Kiểm tra Moodle và restore cục bộ ngày 29/10/2026

Đã chạy `python -m scripts.check_moodle --keep-on-failure` ngoài sandbox Windows với Docker Desktop Linux. Lượt hoàn tất có exit code **0**, report **`status: passed`**, bắt đầu `2026-10-29T15:04:05Z`, kết thúc `2026-10-29T15:07:12Z`. Các lượt trước bị lỗi đăng nhập hoặc timeout restore không được tính là đạt. Lượt này thành công nên không giữ tài nguyên debug.

| Kiểm tra | Kết quả |
|---|---|
| Cài Moodle bằng `configure.php`/`install-db.php`, gọi cài lại | Đạt; lần hai nhận diện database đã cài |
| Phiên bản chạy thực tế | Moodle 4.5.15, PHP 8.3.35, PostgreSQL 16.15 |
| Course, enrolment và quyền teacher/student | Đạt |
| Đăng nhập HTTP admin/teacher/student, tải file có xác thực | Đạt trước và sau restore |
| Người chưa đăng nhập tải file course, truy cập config/`.git` | Bị chặn theo assertion |
| Cron | Đạt trước và sau restore, không phát hiện task failed |
| Dump database và archive file khi web dừng, kiểm tra checksum | Đạt; web được mở lại và thử truy cập sau backup |
| Restore sang database/code/moodledata mới, mật khẩu DB mới | Đạt; user/course/role/file khớp trước backup |
| Ghi và đọc file mới sau restore | Đạt |
| Cleanup của lượt kiểm tra | Đạt; dọn 4 container và 11 volume có nhãn sở hữu |
| Unit test toàn repository, CLI validate và doctor | 29 tests đạt; cấu hình và công cụ hợp lệ; doctor không kiểm tra quyền AWS |

Bằng chứng: `.work/moodle-check/20261029T150405Z-f2cf8aacada6/report.json` và log cùng thư mục (84 bước, gồm kiểm tra readiness và cleanup). File giả trước/sau restore có SHA-256 `75678fd2982aa47d239ff7f0af04b0aa70e69de58ad98d41340b510c1de43c80`. Runtime dùng cùng image ID đã ghi ở phần smoke test. Mã test nằm trong `scripts/check_moodle.py`, `tests/integration/moodle.php` và `tests/test_moodle_check.py`.

Môi trường unit test mới: Python 3.12 và PyYAML 6.0.2 tại `.work/validation-venv/`. Python mặc định và venv MSYS cũ thiếu PyYAML nên lượt chạy bằng các môi trường đó không đạt; chỉ tính kết quả sau khi cài đúng dependency. CI đã bổ sung chạy integration và lưu artifact; chưa chạy trên GitHub trong phiên này.

Đây là dump/archive/restore trong Docker cục bộ, **không chạy `bootstrap.sh`, `backup.sh`, `health.sh` hay systemd trên EC2**. Chưa thử nghiệp vụ student nộp bài/teacher xem bài, reboot, backup S3 hoặc đo tải. Kết quả này hoàn tất kiểm tra ứng dụng local của small, chưa đủ để đóng cổng nghiệm thu small trên AWS.

## Triển khai AWS: lab mới ngày 29/10/2026 (UTC)

- Profile do người vận hành chọn: `mquann`; STS xác nhận phiên hợp lệ. Công cụ AWS CLI 2.38.5 và Terraform 1.16.6 trên máy Windows.
- Tìm thấy một lab `moodle-lab-dev` có EC2 t3.small tạo từ ngày 25/10, nằm ngoài state cục bộ. Người vận hành chọn **dựng lab mới**; tạo `config/small-new.yaml` với project `moodle-lab-v2`, environment `dev`, state riêng tại `.work/moodle-lab-v2-dev/`.
- Plan mới: 10 tạo mới, không sửa/xóa tài nguyên hiện có. Đã kiểm tra tên mới không trùng, AMI Ubuntu 26.04 tìm được trong Singapore, EC2 t3.medium, gp3 30 GiB mã hóa, IMDSv2, SG không ingress, CPU credits standard.
- Apply mới tạo thành công **6 tài nguyên mạng**: VPC, subnet, internet gateway, route table, route table association và security group. AWS từ chối `iam:CreateRole` vì identity policy của profile không cho phép. Chưa có EC2, EBS hay IPv4 mới do lượt apply này.
- Đã lưu state phần tạo thành công, lập lại recovery plan: **4 tạo mới, 0 sửa, 0 xóa** (IAM role, instance profile, attachment chính sách SSM và EC2). Không lặp lại saved plan đã dùng của lượt apply lỗi.
- `ssm:DescribeInstanceInformation`, `iam:SimulatePrincipalPolicy`, `iam:ListRoles`, `cloudtrail:LookupEvents` và `pricing:GetProducts` cũng bị AWS từ chối trong các bước kiểm tra. Các lỗi này không phải bằng chứng các quyền tạo hạ tầng khác đã được cấp; quyền vận hành cần được cấp phù hợp trước nghiệm thu SSM.
- Bucket backup trong cấu hình mới vẫn rỗng. Chưa tạo bucket hoặc cấp quyền S3; backup S3 và lịch backup chưa được cấu hình.

Bằng chứng riêng tư: `.work/moodle-lab-v2-dev/terraform.tfstate`, `recovery-plan.log`, `apply.tfplan`, `apply.json`; bản đối chiếu plan ban đầu nằm trong `plan-review.json`. Giữ nguyên state để tiếp tục sau khi xử lý quyền. Chưa có kết quả cloud-init, Moodle hoặc SSM của lab mới.

Đã chạy IAM Policy Autopilot trên recovery plan và lưu baseline tại `.work/moodle-lab-v2-dev/deployer-policy.autopilot.json`, kèm `admin-handoff.md`. Baseline có wildcard và quyền IAM rộng, cần admin rà soát phạm vi trước sử dụng; chưa gắn policy hoặc thay đổi quyền của người vận hành. JSON plan tạm đã được xóa sau khi sinh policy. Giữ binary saved plan và state riêng tư để tiếp tục triển khai; không commit chúng.

Một lượt apply trước đó với tên cũ bị lỗi DNS EC2/IAM; state cục bộ tên cũ không chứa tài nguyên managed. Lab đang chạy từ ngày 25/10 được nhận diện qua AWS inventory, không phải tài nguyên tạo thành công trong lượt lỗi này. Không dùng state cục bộ rỗng đó để quản lý hoặc suy luận rằng lab cũ không tồn tại.

## Các phần chưa được kiểm chứng tại thời điểm 29/10/2026

- Cloud-init trên EC2 Ubuntu 26.04, cài package thực tế, systemd, reboot và script cài hoàn chỉnh.
- IAM/SSM/S3 trong tài khoản AWS thực tế: đây là trạng thái lịch sử tại lần ghi log này; xem biên bản small hiện tại. Hạn mức ngân sách mới là 150 USD từ 07/11/2026.
- Moodle login/course/upload/cron trên máy mới.
- Backup/restore round trip bằng script systemd/S3 trên EC2, failure recovery và lịch backup thực tế.
- Hiệu năng, HA, khả năng scale, RTO/RPO và hóa đơn.
- GitHub Actions: đã có workflow, chưa chạy trên GitHub trong phiên này.

Đây là các bước còn lại để nghiệm thu triển khai cloud; unit test và Terraform validate không chứng minh chúng đã thành công. Kế hoạch thực hiện và tiêu chí nằm trong `00-project-plan.md` và `06-test-plan.md`.
