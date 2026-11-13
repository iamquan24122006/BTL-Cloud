# Moodle Cloud Distribution — đồ án triển khai LMS trên AWS

**Mục tiêu:** xây dựng quy trình tái lập từ cài Moodle thủ công, tới Terraform, rồi CLI đọc YAML; chứng minh bằng đăng nhập, tạo khóa học, cron, backup và khôi phục.

**Cập nhật ngày 14/11/2026:** bổ sung commit N3 `2440d08` từ khoi: builder có thể chọn `t3.small`, integration kiểm tra purge cache không ảnh hưởng namespace khác và hồ sơ [nghiệm thu/tải N3](docs/evidence/aws-n3-2026-11-11/README.md). Lượt N3 ở account riêng có đủ ba lần lặp 10/25/50 user; 50-user r2/r3 không đạt ngưỡng p95 tương tác 3 giây dù không lỗi nghiệp vụ. Đây không phải kết quả Sydney cũ hoặc bằng chứng medium mới đã triển khai xong. Bản sửa tạo thư mục cha cho load runner cũng được đưa vào source.

**Thông số nhóm:** 4 thành viên; tổng ngân sách AWS **150 USD**, giảm theo yêu cầu ngày 07/11/2026. Giữ tỷ lệ phân bổ hiện có: 112,50 USD cho các giai đoạn và 37,50 USD dự phòng; thời hạn 4 tuần vẫn là giả định chờ chốt. Ưu tiên hoàn tất small; medium cần dự toán lại trong hạn mức còn lại. Xem [phân công 4 người](docs/00-project-plan.md) và [hạn mức chi tiêu](docs/07-report-and-cost.md).

**Bản tích hợp ngày 12/11/2026:** mã small của master và medium của khoi được hợp nhất vào một CLI; xem [cách dùng và kiểm chứng bản tích hợp](docs/17-small-medium-integration.md). Medium đã có [bằng chứng chạy AWS](docs/12-medium-live-lab.md), [HTTPS tại ALB](docs/13-medium-med02.md), và [cleanup ngày 10/11](docs/15-aws-cleanup.md). URL/AMI/ARN của medium trong hồ sơ là lịch sử, cần dựng lại trước demo. Large/production chưa được hỗ trợ.

**Hồ sơ small ngày 08/11/2026:** `small` ở Sydney đã đạt kiểm tra chức năng, backup S3, restore, reboot staging và các ca lỗi phục hồi. **63 unit test chạy lại đều đạt**; CI commit `904c113` trước đó xanh ở cả push và pull request. Cài từng bước trên EC2 sạch đã chạy và kiểm tra nghiệp vụ đầy đủ. Bằng chứng tải riêng trong VPC đã lưu đủ ba lượt 10-user, ba lượt 25-user và hai lượt 50-user, tất cả 0 lỗi; còn thu kết quả lượt 50-user cuối, metric và xác nhận cleanup. Phiên AWS hết hạn khi kiểm tra lại, nên chưa xác minh trạng thái cloud mới. Budget AWS 150 USD và kênh cảnh báo nội bộ đã kiểm chứng trước đó. Còn kiểm tra giao diện và kiểm tra chéo của người nhận để ký P0. Kết quả small này không thay thế hồ sơ medium hoặc nghiệm thu tích hợp. Xem [biên bản small](docs/13-small-acceptance.md), [hướng dẫn bàn giao](docs/14-small-handover.md) và [nhật ký chi tiết](docs/08-validation.md).

**Demo small:** làm theo [kịch bản thao tác 12–15 phút](docs/15-small-demo.md); mở site bằng `.\scripts\demo-small.ps1 -Environment dev -ExpectedAccount <ACCOUNT_ID>`, thay `<ACCOUNT_ID>` bằng account lab đã xác minh. [Danh sách dịch vụ thực tế](docs/16-small-services.md) giải thích vai trò từng dịch vụ AWS và phần mềm trong bản small.

**Lab hiện tại:** [config/sydney.yaml](config/sydney.yaml), tên `moodle-sydney-dev`, region `ap-southeast-2`; staging dùng [config/sydney-staging.yaml](config/sydney-staging.yaml). CLI mặc định dùng cấu hình Sydney; nên luôn truyền `--config` để thấy rõ môi trường đích. Giữ nguyên state riêng trong `.work/moodle-sydney-dev/` và `.work/moodle-sydney-staging/`.

**Lab Singapore cũ:** `config/small-new.yaml` / `moodle-lab-v2-dev` từng dừng sau khi tạo 6 tài nguyên mạng vì thiếu `iam:CreateRole`. [Hướng dẫn IAM cũ](docs/10-iam-permissions.md) chỉ áp dụng lab đó; không dùng policy này để sửa quyền cho Sydney. Chưa đối chiếu lại inventory Singapore trong lượt tiếp tục này.

## Đọc theo thứ tự

**Bàn giao N3 và vòng đời lab:** người dùng đã yêu cầu dọn AWS để ngừng phí. Xem [trạng thái cleanup thực tế](docs/15-aws-cleanup.md) trước khi dùng URL/ARN/AMI lịch sử. [Hướng dẫn N3](docs/14-n3-acceptance-guide.md) trình bày dựng lại, kiểm thử bổ sung, restore, cảnh báo, đo tải và bàn giao; có [mẫu biên bản](docs/templates/n3-run.md) và [ma trận 20 ca](docs/templates/n3-results.csv). Nhánh `master` tích hợp phần N1 từ `mq` và N2 từ `khoi`; luôn chọn đúng YAML, AWS profile và account cho môi trường đích. Cleanup Singapore của N2 không chứng nhận trạng thái account Sydney của N1.

Nếu tiếp tục từ trạng thái mã hiện tại, dùng [hướng dẫn hoàn tất các phần còn thiếu](docs/09-completion-guide.md): build Docker, deploy/kiểm tra small, restore, phát triển medium, đo tải và bàn giao.

1. [Phạm vi, yêu cầu và kế hoạch 4 tuần](docs/00-project-plan.md).
2. [Lựa chọn phiên bản](docs/01-version-decisions.md).
3. [Kiến trúc, luồng dữ liệu và thiết kế mở rộng](docs/02-architecture.md).
4. [Lab cài thủ công trên EC2](docs/03-manual-lab.md).
5. [Terraform và CLI: từ cấu hình đến triển khai](docs/04-deployment.md).
6. [Backup, restore, nâng cấp, rollback và dọn dẹp](docs/05-operations.md).
7. [Kiểm thử, đo tải và bằng chứng nghiệm thu](docs/06-test-plan.md).
8. [Dự toán chi phí, dàn ý báo cáo và kịch bản demo](docs/07-report-and-cost.md).
9. [Medium: hướng dẫn N2, artifact, backend, release và nghiệm thu](docs/10-medium-n2.md).
10. [MED-02: domain miễn phí, ACM, HTTPS tại ALB và bằng chứng](docs/13-medium-med02.md).

## Stack của bản đầu

| Thành phần | Lựa chọn |
|---|---|
| Máy chủ | Ubuntu Server 26.04 LTS, EC2 x86_64; cấu hình mẫu `t3.medium` |
| Web/PHP | Apache + PHP 8.3, OPcache trong Docker; base image Debian Bookworm ghim digest |
| Moodle | 4.5.15, ghim Git tag `v4.5.15` |
| Database | PostgreSQL 16 từ kho PGDG cho `resolute`, trên cùng EC2 |
| File | `moodledata` ngoài webroot, EBS gp3 mã hóa |
| Truy cập lab | SSM port forwarding tới `localhost:8080`; không có ingress SG |
| IaC/tool | Terraform >=1.10,<2; AWS provider 6.x; Python >=3.11 + PyYAML |
| Backup | `pg_dump` + archive file khi dừng ghi; S3 là tùy chọn cấu hình |

Đây là lựa chọn cho một lab học tập. Một EC2 là điểm lỗi đơn; không có HA, domain public, HTTPS public hay RDS ở bản này. Mục tiêu số người dùng chỉ được xác nhận sau khi đo tải. Moodle 4.5 vẫn còn hỗ trợ bảo mật nhưng không phải LTS mới nhất; [ADR phiên bản](docs/01-version-decisions.md) giải thích lựa chọn và đường nâng cấp.

Ubuntu 26.04 là hệ điều hành máy chủ. PHP chạy trong container để giữ phiên bản 8.3 tương thích Moodle 4.5; không cài gói PHP mặc định 8.5 của Ubuntu. Cron, health và backup dùng chung image với web. Xem [lab Ubuntu 26.04](docs/03-manual-lab.md) để thao tác từng bước.

## Chạy cục bộ, không tạo AWS

PowerShell tại thư mục repository:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.moodle_cloud validate
.\.venv\Scripts\python.exe -m src.moodle_cloud render
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Nếu `python` là Microsoft Store alias, dùng đường dẫn tới bản Python đã cài. `render` chỉ tạo `.work/<project>-<environment>/config.tfvars.json`. Không điền mật khẩu vào YAML.

Khi Docker Desktop đang chạy Linux containers, kiểm tra runtime rồi cài/thử Moodle với PostgreSQL và backup/restore cục bộ:

```powershell
python -m scripts.check_runtime
python -m scripts.check_moodle
```

Hai lệnh không gọi AWS; report nằm trong `.work/runtime-check/` và `.work/moodle-check/`. Kiểm thử ứng dụng dùng dữ liệu giả, tự dọn container/volume riêng và không thay thế nghiệm thu trên EC2. Xem [phạm vi kiểm thử](docs/06-test-plan.md).

```powershell
python -m src.moodle_cloud doctor
python -m src.moodle_cloud --config config/dev.yaml plan
# Xem tài nguyên và chi phí trước bước tiếp theo.
python -m src.moodle_cloud --config config/dev.yaml apply --confirm moodle-lab-dev
python -m src.moodle_cloud status
```

`plan/apply` cần AWS CLI có phiên đăng nhập hợp lệ và Terraform trong PATH. `apply` phát sinh tài nguyên tính phí. Không xem việc Terraform hoàn tất là Moodle đã sẵn sàng: còn phải kiểm tra cloud-init và chức năng ứng dụng.

## Cấu trúc

```text
config/        YAML theo môi trường, không chứa secret
docs/          Kế hoạch, sơ đồ và các runbook
infra/small/   Terraform: VPC, subnet, IAM, SG, EC2
infra/medium/  Terraform: hai AZ, ALB/ASG, RDS, EFS, Redis, runner, CloudWatch
infra/backend/ Bootstrap bucket state riêng (versioning/encryption/public access block)
scripts/       Host setup, Dockerfile, bootstrap, PHP CLI, health, backup
scripts/medium/ Runtime nhiều node và operations có khóa chung
src/           CLI Python
tests/         Kiểm tra đầu vào và chốt an toàn của CLI
.work/         State/plan/artifact cục bộ, không commit
```

Mật khẩu được sinh trên EC2. State và saved plan vẫn là dữ liệu riêng tư: không chia sẻ, không commit. Backup chứa dữ liệu người học và `config.php`; bảo vệ quyền truy cập tương ứng.

## Đóng góp của distribution

Điểm khác biệt là quy trình cài có kiểm soát, cấu hình lab thống nhất, CLI kiểm tra đầu vào, kế hoạch trước áp dụng, cron có log, backup có checksum và quy trình restore. Bản đầu dùng theme Boost đi kèm Moodle. Plugin bên ngoài chỉ thêm sau khi kiểm tra tương thích và ghim phiên bản; chưa có tính năng tự cài plugin.
