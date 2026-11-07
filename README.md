# Moodle Cloud Distribution — đồ án triển khai LMS trên AWS

**Mục tiêu:** xây dựng quy trình tái lập từ cài Moodle thủ công, tới Terraform, rồi CLI đọc YAML; chứng minh bằng đăng nhập, tạo khóa học, cron, backup và khôi phục.

**Thông số nhóm:** 4 thành viên; tổng ngân sách AWS **150 USD**, giảm theo yêu cầu ngày 07/11/2026. Giữ tỷ lệ phân bổ hiện có: 112,50 USD cho các giai đoạn và 37,50 USD dự phòng; thời hạn 4 tuần vẫn là giả định chờ chốt. Ưu tiên hoàn tất small; medium cần dự toán lại trong hạn mức còn lại. Xem [phân công 4 người](docs/00-project-plan.md) và [hạn mức chi tiêu](docs/07-report-and-cost.md).

**Tình trạng ngày 07/11/2026 UTC:** `small` ở Sydney đã đạt kiểm tra chức năng, backup S3, restore, reboot staging và các ca lỗi phục hồi. **63 unit test đạt**; CI commit `904c113` xanh ở cả push và pull request. Cài từng bước trên EC2 sạch đã chạy và kiểm tra nghiệp vụ đầy đủ. Ma trận tải riêng trong VPC đã đạt ba lượt 10-user và ba lượt 25-user, đang chạy các lượt 50-user; chưa chốt kết luận tải hay cleanup. Budget AWS 150 USD và kênh cảnh báo nội bộ đã kiểm chứng. Còn kiểm tra giao diện/demo và kiểm tra chéo của người nhận để ký P0. `medium`/`large` vẫn là thiết kế mở rộng. Xem [biên bản small](docs/13-small-acceptance.md), [hướng dẫn bàn giao](docs/14-small-handover.md) và [nhật ký chi tiết](docs/08-validation.md).

**Lab hiện tại:** [config/sydney.yaml](config/sydney.yaml), tên `moodle-sydney-dev`, region `ap-southeast-2`; staging dùng [config/sydney-staging.yaml](config/sydney-staging.yaml). CLI mặc định dùng cấu hình Sydney; nên luôn truyền `--config` để thấy rõ môi trường đích. Giữ nguyên state riêng trong `.work/moodle-sydney-dev/` và `.work/moodle-sydney-staging/`.

**Lab Singapore cũ:** `config/small-new.yaml` / `moodle-lab-v2-dev` từng dừng sau khi tạo 6 tài nguyên mạng vì thiếu `iam:CreateRole`. [Hướng dẫn IAM cũ](docs/10-iam-permissions.md) chỉ áp dụng lab đó; không dùng policy này để sửa quyền cho Sydney. Chưa đối chiếu lại inventory Singapore trong lượt tiếp tục này.

## Đọc theo thứ tự

Nếu tiếp tục từ trạng thái mã hiện tại, dùng [hướng dẫn hoàn tất các phần còn thiếu](docs/09-completion-guide.md): build Docker, deploy/kiểm tra small, restore, phát triển medium, đo tải và bàn giao.

1. [Phạm vi, yêu cầu và kế hoạch 4 tuần](docs/00-project-plan.md).
2. [Lựa chọn phiên bản](docs/01-version-decisions.md).
3. [Kiến trúc, luồng dữ liệu và thiết kế mở rộng](docs/02-architecture.md).
4. [Lab cài thủ công trên EC2](docs/03-manual-lab.md).
5. [Terraform và CLI: từ cấu hình đến triển khai](docs/04-deployment.md).
6. [Backup, restore, nâng cấp, rollback và dọn dẹp](docs/05-operations.md).
7. [Kiểm thử, đo tải và bằng chứng nghiệm thu](docs/06-test-plan.md).
8. [Dự toán chi phí, dàn ý báo cáo và kịch bản demo](docs/07-report-and-cost.md).

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
scripts/       Host setup, Dockerfile, bootstrap, PHP CLI, health, backup
src/           CLI Python
tests/         Kiểm tra đầu vào và chốt an toàn của CLI
.work/         State/plan/artifact cục bộ, không commit
```

Mật khẩu được sinh trên EC2. State và saved plan vẫn là dữ liệu riêng tư: không chia sẻ, không commit. Backup chứa dữ liệu người học và `config.php`; bảo vệ quyền truy cập tương ứng.

## Đóng góp của distribution

Điểm khác biệt là quy trình cài có kiểm soát, cấu hình lab thống nhất, CLI kiểm tra đầu vào, kế hoạch trước áp dụng, cron có log, backup có checksum và quy trình restore. Bản đầu dùng theme Boost đi kèm Moodle. Plugin bên ngoài chỉ thêm sau khi kiểm tra tương thích và ghim phiên bản; chưa có tính năng tự cài plugin.
