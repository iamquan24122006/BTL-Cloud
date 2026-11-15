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

Bản sửa đã có kiểm thử cục bộ; triển khai AWS, CI đúng commit và kết quả sau triển khai đang được thực hiện. Chưa dùng trang này để khẳng định toàn bộ dự án đã nghiệm thu. Ma trận đầy đủ tại [hồ sơ chốt](18-project-closeout.md).
