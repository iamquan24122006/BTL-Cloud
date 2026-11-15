# Hoàn thiện vận hành — 15/11/2026

## Lỗi phát hiện lại trên AWS

- Backup theo lịch lúc 02:00 UTC trả exit 1; lệnh backup trước sửa tranh khóa PostgreSQL với cron đang chạy.
- `core\task\tag_cron_task` thất bại với `permission denied for table mdl_tag_correlation` tại `TRUNCATE TABLE mdl_tag_correlation`. Runtime có `DELETE` nhưng thiếu `TRUNCATE`.
- Cron vẫn chạy các tác vụ khác, website không bị maintenance; không lấy tình trạng timer active làm bằng chứng cron hoàn toàn khỏe.

## Thay đổi trong mã

Backup lấy khóa local, tạm dừng timer cron và đợi tác vụ hiện tại kết thúc trước khi lấy khóa cluster. Timeout 15 phút, không giết worker; trả timer về trạng thái ban đầu trên cả đường thành công và lỗi, giữ maintenance khi backup lỗi. PostgreSQL connection được đóng trước khi khởi động timer trở lại. Có kiểm thử tranh backup, timeout, lỗi upload, app node bị từ chối và timer vốn inactive.

Runtime nhận thêm quyền `TRUNCATE` cho các bảng thường/partition của Moodle. Migration vẫn giữ ownership và quyền schema. Integration chạy tác vụ tag thật để bắt lỗi tương thích này.

Host bundle được phát hành ở key mới có source commit và SHA-256; không ghi đè bundle cũ. Image Moodle có digest/release riêng và có thể giữ nguyên khi chỉ đổi mã chạy trên host. Bằng chứng triển khai phải ghi riêng hai nguồn này.

## Trạng thái xác minh

**Đã triển khai và kiểm chứng trên Sydney ngày 15/11/2026.** Bundle host mới (`ae885c1d238f`, SHA-256 `f135174d…`) được phát hành dưới key mới, image/release giữ nguyên. Runner mới `i-0d43470f88eb13a58`, ASG refresh `Successful`, release hoàn tất lúc `07:09:13Z`.

- Trước sửa: `moodle_runtime` không có `TRUNCATE` trên 0/494 bảng; `tag_cron_task` có `faildelay=7680`, `lastruntime=0`, cron dừng ở `cron-audit.php` và để lại `worker-pending.json`.
- Sau sửa: tag task chạy thành công, `faildelay=0`, 494/494 bảng có `TRUNCATE`, cron kết thúc `cron-completed-and-task-audit-clear`, plan cuối `No changes`, 47/47 ca HTTPS đạt.
- Small: `verify_backup.py` dev/staging được cập nhật qua SSM lên `59063f33…`; backup dev chạy đủ, upload S3 và manifest ghi `cron drained`. Không thay EC2 small.
- Ngay sau release, `unattended-upgrades` trên runner restart containerd và kill worker `cron.php`; wrapper giữ marker nên cron dừng khoảng 15 phút cho tới khi review. Đã phục hồi `07:33:35Z`, chu kỳ kế `07:36:38Z` sạch. Alarm `CronSuccess-missing` không chuyển ALARM trong khoảng trống — còn mở để kiểm chứng.

[Bằng chứng chi tiết](evidence/hostfix-2026-11-15/README.md), [runbook phát hành](27-host-bundle-deploy.md). Ma trận đầy đủ tại [hồ sơ chốt](18-project-closeout.md); trang này không khẳng định toàn bộ dự án đã nghiệm thu.
