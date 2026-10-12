# Nhật ký kiểm chứng repository

Chuẩn bị trong phiên làm việc 07–08/10/2026. Đã cập nhật mã và tài liệu theo Ubuntu Server 26.04; chưa kết nối tài khoản AWS để deploy.

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
| Base image PHP | Đã lấy digest từ Docker Registry để ghim Dockerfile; chưa build image |

Runtime kiểm tra: Python 3.12, PyYAML 6.0.2, Terraform 1.13.4 trên Windows. Terraform zip tải từ HashiCorp, checksum SHA-256 đã đối chiếu file phát hành. Trong lượt kiểm tra Ubuntu 26.04, sandbox chặn thư mục tạm của Python, provider Terraform không phản hồi và Git Bash bị chặn khởi động. Đã chạy lại các kiểm tra tương ứng ngoài sandbox với quyền được cho phép: 19 unit test, 2 mock test Terraform và kiểm tra Bash đều đạt. Không gọi AWS thật.

Khi chạy thử đầu tiên, test SG phát hiện thuộc tính ingress chưa xác định ở bước plan. Đã sửa cấu hình thành `ingress = []` và cả hai mock test đạt. Khi rà soát backup, đã sửa chờ cron để tính cả trạng thái `activating` của systemd oneshot. Bundle chuyển file dùng base64 theo dòng ngắn để phù hợp paste qua terminal.

Thay đổi Ubuntu 26.04 gồm AMI, host setup PGDG/Docker, PHP 8.3 container, image ID dùng chung cho mọi runner, systemd web/cron và metadata runtime trong backup format 2. Runbook cài tay, restore và CI đã được sửa tương ứng. Đối chiếu nguồn tại [ADR phiên bản](01-version-decisions.md), [gói Docker](https://packages.ubuntu.com/resolute/docker.io), [Buildx](https://packages.ubuntu.com/resolute/docker-buildx) và [AWS CLI](https://packages.ubuntu.com/resolute/awscli).

## Chưa được kiểm chứng

- Docker build, Apache chạy trong container và PHP lint: máy hiện tại chưa có Docker/PHP; CI đã có các bước build/config check/extension check/lint nhưng chưa chạy trên GitHub.
- Cloud-init trên EC2 Ubuntu 26.04, cài package thực tế, systemd, reboot và script cài hoàn chỉnh.
- IAM/SSM/S3 trong tài khoản AWS thực tế; tài khoản và budget chưa được cung cấp.
- Moodle login/course/upload/cron trên máy mới.
- Backup/restore round trip, failure recovery và lịch backup thực tế.
- Hiệu năng, HA, khả năng scale, RTO/RPO và hóa đơn.
- GitHub Actions: đã có workflow, chưa chạy trên GitHub trong phiên này.

Đây là các bước còn lại để nghiệm thu triển khai cloud; unit test và Terraform validate không chứng minh chúng đã thành công. Kế hoạch thực hiện và tiêu chí nằm trong `00-project-plan.md` và `06-test-plan.md`.
