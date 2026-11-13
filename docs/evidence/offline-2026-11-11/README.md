# Kiểm thử offline ngày 11/11/2026

Mã được kiểm tra: nhánh `khoi`, commit `82e95c9849ec4ac4a061b6650c5ab2cbe01d995e`; working tree sạch khi bắt đầu. Người thực hiện: Codex. Chưa có reviewer độc lập. Không chạy AWS CLI, Terraform plan/apply/destroy, không tạo tài nguyên AWS. Có tải dependency/provider/image và upstream Moodle qua Internet để kiểm thử cục bộ.

## Kết quả thực chạy

| Phạm vi | Kết quả | Bằng chứng |
|---|---|---|
| Python unit tests | 40/40 đạt | [unit.log](unit.log) |
| CLI small/medium | Validate và render đều đạt | [checks.json](checks.json) |
| Bundle | Medium và manual tạo thành công; unit test kiểm tính xác định của medium bundle đạt | [checks.json](checks.json) |
| Python/Bash | Compile Python đạt; kiểm cú pháp 12 shell script đạt | [checks.json](checks.json) |
| Terraform format | Toàn bộ `infra` đạt | [checks.json](checks.json) |
| Terraform validate | Cả 5 root small, medium, backend, medium_support, medium_builder đạt | [checks.json](checks.json) |
| Terraform mock tests | Small 2/2, medium 2/2 đạt | [small](small-test.log), [medium](medium-test.log) |
| PHP/Apache smoke | Build và toàn bộ kiểm tra đạt; PHP 8.3.35; web/CLI thống nhất, code readonly; hai URL nhạy cảm trả 403 | [php-runtime.json](php-runtime.json) |
| PHP medium syntax | 8/8 file đạt | [php-lint.log](php-lint.log) |
| Medium local integration | 45/45 bước đạt | [medium-runtime.json](medium-runtime.json) |
| Cleanup local | Truy vấn Docker sau test không còn container/volume/network có prefix `moodle-n2-` | Xác minh trực tiếp sau khi script hoàn tất |

Smoke PHP chạy từ `2026-11-11T14:55:08Z` tới `15:00:22Z`; integration medium từ `15:01:34Z` tới `15:05:20Z` (22:01–22:05 giờ Việt Nam). Báo cáo JSON giữ timestamp đầy đủ.

## Integration medium đã chứng minh gì

- Cài schema Moodle thật, tạo MUC mapping và chạy lại mapping thành công.
- Driver Moodle `pgsql` dùng `verify-full`, kết nối TLS 1.3: [TLS proof](tls-proof.log).
- Cache ghi tại A, đọc tại B; file tên tiếng Việt qua shared volume đúng checksum.
- Hai tiến trình tranh khóa: một giữ được khóa, một nhận BUSY.
- Đăng nhập thật, dùng cùng cookie qua hai app và sau purge MUC; Redis session vẫn còn.
- Readiness lỗi khi Redis session dừng, phục hồi khi Redis chạy lại.
- Maintenance gate chặn request trực tiếp app B bằng 503.

Các file PHP, Apache và Moodle chạy trong Linux container. Docker shared volume không chứng minh EFS; PostgreSQL/Redis local không chứng minh RDS/ElastiCache hay mạng AWS.

## Môi trường và giới hạn tái lập

- Windows, Python 3.14.8, PyYAML 6.0.2 ở chế độ Python thuần, Terraform 1.16.6, Docker Engine 29.8.0 Linux amd64. CI trong repository dùng Python 3.12 và Terraform 1.13.4; lượt này không thay thế CI đó.
- `python` đầu tiên trong PATH trỏ tới MSYS và không hoạt động đúng. Dùng Python Windows để tạo `.venv`.
- Cài `requirements.txt` bình thường trên Python 3.14 thất bại tại build PyYAML/Cython do Application Control chặn extension. Để giữ nguyên dependency đã ghim, tải wheel PyYAML 6.0.2 cho CPython 3.13 và chỉ trích xuất các file `yaml/*.py` vào `.work/offline-deps/pure`; không chạy hay cài extension nhị phân khác ABI. Runner đặt `PYTHONPATH` tới thư mục này. Đây là cách chạy test tạm, chưa chứng nhận cài dependency thông thường trên Python 3.14.
- Terraform cần chạy ngoài sandbox mới truy cập được executable/provider; Docker Desktop đã được khởi động để chạy test. Không đổi mã ứng dụng, requirements hoặc workflow.
- Image kiểm thử medium có revision toàn số 0 theo CI và chỉ dùng local; không được dùng làm release deploy. Hai image kiểm thử được giữ local làm cache; Docker Desktop vẫn đang chạy.
- Chưa kiểm chứng small mới ở nhánh `mq`, GitHub Actions remote, browser desktop/mobile, upload lớn, LMS đủ vai trò, cron/systemd trên EC2, S3 backup/restore, HTTPS public, ASG, IAM, alarm, đo tải hoặc chi phí.

## Liên hệ nghiệm thu

AT-01/02 có bằng chứng unit/mock cho validate đầu vào và chốt plan/config/account/confirm. MED-03/04/05/06/08/10 có bằng chứng tích hợp local cho các hành vi nêu trên. Các ca AT yêu cầu AWS vẫn để **Chờ nghiệm thu**; không đánh dấu toàn bộ AT-12…17 đạt từ lượt local này.

Log đầy đủ: `.work/offline-20261111T145415Z/`, `.work/runtime-check/20261111T145508Z-5a44ca91/`, `.work/medium-offline-runtime/`, `.work/medium-offline-build.log`. Không chia sẻ thư mục `private/` của integration vì chứa credential và khóa TLS thử nghiệm. Runner tạm nằm ở `.work/run_offline.py`.

Lượt offline không phát hiện lỗi mã trong phạm vi đã chạy. Cần một thành viên khác kiểm tra lại bằng chứng trước khi ký nghiệm thu nhóm.
