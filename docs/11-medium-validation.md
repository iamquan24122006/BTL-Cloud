# Kết quả kiểm tra mã N2

Ngày kiểm tra: 06/11/2026. Checkout local: `master`, thay đổi chưa commit/push. Không tạo, sửa hoặc xóa tài nguyên AWS trong lần phát triển này. Không dùng kết quả dưới đây để ghi `Đạt` cho ca nghiệm thu AWS.

| Phạm vi | Kết quả thực chạy |
|---|---|
| Python unit tests | **39 test đạt**: schema small/medium, input âm, offline render, state isolation/backend lock config, fingerprint, saved plan/account/confirmation/single use, race đổi plan, worker timeout và migration bị gián đoạn |
| Validate/render CLI | Small và YAML medium mẫu hợp lệ; render medium tách workspace và không xuất backend vào tfvars |
| Terraform medium | `fmt -check`, `validate` đạt; **1 mock test đạt**, toàn bộ resource/data được mock, không gọi AWS |
| Terraform backend | `fmt -check`, `validate` đạt; chưa apply bucket |
| Shell/Python/PHP | Shell syntax và Python compile đạt; tất cả PHP medium lint đạt trong image build |
| Image medium | Build Linux amd64 đạt, PHP 8.3, Redis extension 6.1.0, Moodle tag 4.5.15 được đối chiếu upstream commit |
| Docker integration | **45 bước đạt** với Moodle thật, PostgreSQL 16 TLS và hai Redis TLS, hai app container, shared Docker volume |
| Cleanup kiểm thử | Không còn container, volume hoặc network có prefix `moodle-n2-` sau chạy |
| GitHub Actions | Workflow được cập nhật; chưa có bằng chứng một lượt chạy GitHub Actions trên remote |

Integration hoàn tất lúc `2026-11-06T13:00:55Z` (20:00:55 giờ Việt Nam). Image kiểm thử có ID `sha256:f0ae918886cc11f0524bf4515d8654c4f9b1834cde037c9343e3e773829e2ebf`, release label toàn số 0; **không dùng như artifact release để deploy**.

Các ca tích hợp đã chạy:

- Cài schema và tài khoản admin bằng CLI Moodle chuẩn.
- Tạo MUC mapping rồi chạy lại mapping thành công.
- Lấy TLS proof từ chính native database driver của Moodle: `verify-full`, TLS 1.3.
- Ghi cache ở A, đọc đúng ở B; ghi/đọc file tiếng Việt qua shared volume và so SHA-256.
- Hai tiến trình tranh cùng Moodle Lock API: một tiến trình `ACQUIRED`, tiến trình còn lại `BUSY`.
- Đăng nhập bằng form thật; dùng cùng cookie qua A/B; purge cache rồi dùng lại chính cookie đó và vẫn đúng admin.
- Readiness 200 khi dependency dùng được; dừng Redis session thì 503; khởi động lại Redis thì readiness phục hồi.
- Bật maintenance marker rồi gọi thẳng app B: HTTP 503, độc lập với ALB.

Báo cáo và log local nằm ở `.work/medium-runtime-check-final/`; kết quả tổng hợp là `report.json`. Script chạy lại: `python -m scripts.check_medium_runtime --image <validation-image>`. Chỉ chia sẻ report và log đã lọc, không chia sẻ thư mục `private/` chứa credential kiểm thử/certificate. CI upload có giới hạn riêng, không upload `private/`.

Hai lỗi phát hiện và đã sửa trong tích hợp: cấu hình `reverseproxy` không phù hợp public Host của ALB gây login 500; xóa MUC store đã có mapping làm release chạy lại thất bại. Bộ kiểm tra hiện tái hiện hai luồng này.

Docker shared volume không phải EFS; local PostgreSQL/Redis không phải RDS/ElastiCache. Test HTTP nội bộ mô phỏng header của proxy, không chứng minh domain/ACM/HTTPS public. AMI Ubuntu 26.04, EFS TLS/IAM, S3 lock thực, quyền IAM, SSM dừng writer, ASG thay node, backup/restore medium trên AWS và bộ fixture teacher/student vẫn **Chờ nghiệm thu**. Đầu vào và checklist ở [bàn giao N2](10-medium-n2.md).
